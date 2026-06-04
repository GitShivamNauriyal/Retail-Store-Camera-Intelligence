from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Dict, Any

from app.database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/conversion", response_model=Dict[str, Any])
async def get_conversion_rate(db: AsyncSession = Depends(get_db)):
    """
    Calculates Store Conversion Rate (Total Unique POS Transactions / Total Unique Entries).
    Uses a fuzzy time-window match to correlate TrackedEvent (queue checkout) with pos_transactions.
    """
    
    # Count total unique entries
    entries_query = """
    SELECT COUNT(DISTINCT visitor_id) as total_entries 
    FROM tracked_events 
    WHERE event_type = 'ENTRY' OR event_type = 'entry'
    """
    
    # Count total unique POS transactions overall
    total_pos_query = "SELECT COUNT(DISTINCT order_id) as total_transactions FROM pos_transactions"
    
    # Fuzzy match logic:
    # Match pos_transactions to tracked_events where the event occurred in the BILLING zone
    # and the timestamps are within 180 seconds (3 minutes) of each other.
    matched_query = """
    SELECT COUNT(DISTINCT pt.order_id) as matched_transactions
    FROM pos_transactions pt
    JOIN tracked_events te ON pt.store_id = te.store_id 
    WHERE (te.zone_id ILIKE '%BILLING%' OR te.zone_name ILIKE '%BILLING%' OR te.zone_type ILIKE '%BILLING%')
    AND ABS(EXTRACT(EPOCH FROM (te.timestamp - pt.transaction_timestamp))) <= 180
    """
    
    try:
        entries_result = await db.execute(text(entries_query))
        total_entries = entries_result.scalar() or 0
        
        pos_result = await db.execute(text(total_pos_query))
        total_pos = pos_result.scalar() or 0
        
        matched_result = await db.execute(text(matched_query))
        matched_transactions = matched_result.scalar() or 0

        conversion_rate = 0.0
        if total_entries > 0:
            # Conversion rate based on the fuzzy matched POS transactions mapped to real users
            conversion_rate = (matched_transactions / total_entries) * 100.0

        return {
            "total_entries": total_entries,
            "total_pos_transactions": total_pos,
            "matched_transactions": matched_transactions,
            "conversion_rate_percentage": round(conversion_rate, 2),
            "fuzzy_match_window": "+/- 3 minutes"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/demographics", response_model=Dict[str, Any])
async def get_demographics_aov(db: AsyncSession = Depends(get_db)):
    """
    Calculates Average Order Value (AOV) grouped by age_bucket and gender_pred.
    Uses fuzzy matched data from TrackedEvents and pos_transactions.
    """
    
    # Fuzzy match and group by metadata fields
    # PostgreSQL jsonb/json extraction: ->> operator
    aov_query = """
    SELECT 
        COALESCE(te.metadata_json->>'age_bucket', 'Unknown') as age_bucket,
        COALESCE(te.metadata_json->>'gender', te.metadata_json->>'gender_pred', 'Unknown') as gender,
        COUNT(DISTINCT pt.order_id) as order_count,
        SUM(pt.total_amount) as total_revenue,
        AVG(pt.total_amount) as average_order_value
    FROM pos_transactions pt
    JOIN tracked_events te ON pt.store_id = te.store_id 
    WHERE (te.zone_id ILIKE '%BILLING%' OR te.zone_name ILIKE '%BILLING%' OR te.zone_type ILIKE '%BILLING%')
    AND ABS(EXTRACT(EPOCH FROM (te.timestamp - pt.transaction_timestamp))) <= 180
    GROUP BY age_bucket, gender
    ORDER BY total_revenue DESC
    """
    
    try:
        result = await db.execute(text(aov_query))
        rows = result.fetchall()
        
        demographics_data = []
        for row in rows:
            demographics_data.append({
                "age_bucket": row.age_bucket,
                "gender": row.gender,
                "order_count": row.order_count,
                "total_revenue": round(float(row.total_revenue), 2) if row.total_revenue else 0.0,
                "average_order_value": round(float(row.average_order_value), 2) if row.average_order_value else 0.0
            })
            
        return {
            "data": demographics_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
