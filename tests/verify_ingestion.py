import asyncio
import json
import uuid
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://store_admin:store_secure_pass@127.0.0.1:5433/store_intelligence"
REDIS_URL = "redis://localhost:6379"

async def test():
    # 1. Connect to Redis and push event
    print("Connecting to Redis...")
    redis_client = Redis.from_url(REDIS_URL, decode_responses=True)
    
    event_id = str(uuid.uuid4())
    event_data = {
        "event_id": event_id,
        "event_type": "entry",
        "id_token": "ID_TEST_999",
        "store_code": "store_test_999",
        "camera_id": "cam_test_999",
        "event_timestamp": "2026-03-08T18:10:05.120000",
        "is_staff": False,
        "gender_pred": "F",
        "age_pred": 28,
        "age_bucket": "25-34"
    }
    
    print(f"Adding test event to stream with ID {event_id}...")
    await redis_client.xadd("store_events_stream", {"payload": json.dumps(event_data)})
    await redis_client.aclose()
    
    # 2. Wait for ingestion worker to run
    print("Waiting for ingestion worker...")
    await asyncio.sleep(2)
    
    # 3. Connect to Database and query event
    print("Connecting to Database...")
    engine = create_async_engine(DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        result = await session.execute(
            text("SELECT event_id, store_id, visitor_id, event_type, timestamp, metadata_json FROM tracked_events WHERE event_id = :eid"),
            {"eid": uuid.UUID(event_id)}
        )
        row = result.fetchone()
        if row:
            print("\nSUCCESS! Event successfully ingested and verified in PostgreSQL:")
            print(f"Event ID: {row[0]}")
            print(f"Store ID: {row[1]}")
            print(f"Visitor ID: {row[2]}")
            print(f"Event Type: {row[3]}")
            print(f"Timestamp: {row[4]}")
            print(f"Metadata: {row[5]}")
        else:
            print("\nFAILURE: Event not found in PostgreSQL database.")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test())
