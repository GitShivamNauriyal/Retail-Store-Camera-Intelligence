from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db, get_redis_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "unhealthy"
    redis_status = "unhealthy"
    
    # Check Database
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Healthcheck Database connection failed: {e}")
        
    # Check Redis
    redis_client = get_redis_client()
    try:
        await redis_client.ping()
        redis_status = "healthy"
    except Exception as e:
        logger.error(f"Healthcheck Redis connection failed: {e}")
    finally:
        await redis_client.aclose()

    status = "healthy" if db_status == "healthy" and redis_status == "healthy" else "unhealthy"
    
    return {
        "status": status,
        "database": db_status,
        "redis": redis_status
    }
