import asyncio
import json
import logging
from datetime import datetime
import uuid
from typing import Dict, Any, Optional

from sqlalchemy.dialects.postgresql import insert
from app.database import get_redis_client, async_session
from app.models import TrackedEvent

logger = logging.getLogger(__name__)

# Global worker controls
bg_task: Optional[asyncio.Task] = None
stop_event = asyncio.Event()

def parse_timestamp(ts_str: Optional[str]) -> datetime:
    if not ts_str:
        return datetime.utcnow()
    try:
        # Remove 'Z' if present and convert to standard format
        clean_ts = ts_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean_ts)
    except Exception as e:
        logger.warning(f"Failed to parse ISO timestamp '{ts_str}', fallback to UTC now. Error: {e}")
        return datetime.utcnow()

def normalize_event(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        # 1. Parse Event ID (UUID)
        raw_id = data.get("event_id")
        if not raw_id:
            # Generate UUID if not present
            event_id = uuid.uuid4()
        else:
            try:
                event_id = uuid.UUID(str(raw_id))
            except ValueError:
                event_id = uuid.uuid4()

        # 2. Extract Event Type
        event_type = data.get("event_type", "").upper()
        if not event_type:
            logger.warning("Skipping event with missing event_type")
            return None

        # Normalize typical lower-case/alternate event names
        type_mappings = {
            "ZONE_ENTERED": "ZONE_ENTER",
            "ZONE_EXITED": "ZONE_EXIT",
            "ENTRY": "ENTRY",
            "EXIT": "EXIT",
        }
        event_type = type_mappings.get(event_type, event_type)

        # 3. Extract Store ID / Store Code
        store_id = data.get("store_id") or data.get("store_code")
        if store_id:
            store_id = str(store_id).upper()

        # 4. Extract Camera ID
        camera_id = data.get("camera_id")

        # 5. Extract Visitor ID / ID Token / Track ID
        visitor_id = data.get("visitor_id") or data.get("id_token")
        if not visitor_id and "track_id" in data:
            visitor_id = f"TRACK_{data['track_id']}"
        if not visitor_id:
            visitor_id = "UNKNOWN"

        # 6. Parse Timestamp
        raw_ts = data.get("timestamp") or data.get("event_timestamp") or data.get("event_time")
        timestamp = parse_timestamp(raw_ts)

        # 7. Extract Zone ID
        zone_id = data.get("zone_id")

        # 8. Extract Dwell Time
        dwell_ms = data.get("dwell_ms", 0)
        # If wait_seconds is provided (queue events), convert to ms
        if "wait_seconds" in data and not dwell_ms:
            dwell_ms = int(data["wait_seconds"]) * 1000

        # 9. Extract Staff flag
        is_staff = data.get("is_staff", False)
        if isinstance(is_staff, str):
            is_staff = is_staff.lower() == "true"

        # 10. Extract Confidence
        confidence = data.get("confidence", 1.0)
        try:
            confidence = float(confidence)
        except (ValueError, TypeError):
            confidence = 1.0

        # 11. Pack metadata
        # Exclude base columns from metadata to avoid redundancy
        base_keys = {
            "event_id", "store_id", "store_code", "camera_id", "visitor_id", 
            "id_token", "track_id", "event_type", "timestamp", "event_timestamp", 
            "event_time", "zone_id", "dwell_ms", "is_staff", "confidence"
        }
        metadata_dict = {k: v for k, v in data.items() if k not in base_keys}
        
        # Merge inline metadata if it exists
        inbound_meta = data.get("metadata")
        if isinstance(inbound_meta, dict):
            metadata_dict.update(inbound_meta)

        return {
            "event_id": event_id,
            "store_id": store_id,
            "camera_id": camera_id,
            "visitor_id": visitor_id,
            "event_type": event_type,
            "timestamp": timestamp,
            "zone_id": zone_id,
            "dwell_ms": dwell_ms,
            "is_staff": is_staff,
            "confidence": confidence,
            "metadata_json": metadata_dict
        }
    except Exception as e:
        logger.error(f"Error normalizing event: {e}", exc_info=True)
        return None

async def run_ingestion_loop():
    redis_client = get_redis_client()
    last_id = "0-0"
    
    logger.info("Redis Stream Consumer Worker started. Listening on 'store_events_stream'...")
    
    # Check if stream exists or initialize
    try:
        # Create group/stream if not exists (using XGROUP CREATE if we want,
        # but simple XREAD is perfectly sufficient for host-worker single thread setup)
        pass
    except Exception as e:
        logger.warning(f"Error checking stream status: {e}")

    while not stop_event.is_set():
        try:
            # Poll Redis Stream with block=1000 (1 second block time)
            streams = await redis_client.xread(
                streams={"store_events_stream": last_id}, 
                count=100, 
                block=1000
            )
            
            if not streams:
                await asyncio.sleep(0.1)
                continue
                
            for stream_name, messages in streams:
                event_values = []
                for msg_id, payload in messages:
                    # Update offset ID to avoid reading this message again
                    last_id = msg_id
                    
                    # Inspect payload for json event
                    event_data = None
                    if "event" in payload:
                        try:
                            event_data = json.loads(payload["event"])
                        except Exception:
                            pass
                    elif "payload" in payload:
                        try:
                            event_data = json.loads(payload["payload"])
                        except Exception:
                            pass
                    
                    if not event_data:
                        event_data = payload
                    
                    normalized = normalize_event(event_data)
                    if normalized:
                        event_values.append(normalized)
                
                # Bulk upsert using Postgres ON CONFLICT DO NOTHING
                if event_values:
                    async with async_session() as session:
                        stmt = insert(TrackedEvent).values(event_values)
                        stmt = stmt.on_conflict_do_nothing(index_elements=["event_id"])
                        await session.execute(stmt)
                        await session.commit()
                        logger.info(f"Ingested batch of {len(event_values)} events into PostgreSQL.")
                        
        except Exception as e:
            logger.error(f"Error in background ingestion loop: {e}", exc_info=True)
            await asyncio.sleep(2)
            
    await redis_client.aclose()
    logger.info("Redis Stream Ingestion Worker stopped.")

async def start_background_worker():
    global bg_task, stop_event
    stop_event.clear()
    bg_task = asyncio.create_task(run_ingestion_loop())
    logger.info("Background ingestion task created.")

async def stop_background_worker():
    global bg_task, stop_event
    if bg_task:
        logger.info("Stopping background ingestion worker...")
        stop_event.set()
        try:
            await asyncio.wait_for(bg_task, timeout=5.0)
        except asyncio.TimeoutError:
            bg_task.cancel()
        logger.info("Background ingestion worker stopped.")
