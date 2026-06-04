import logging
from fastapi import FastAPI
from app.database import engine
from app.models import Base
from app.health import router as health_router
from app.routes.analytics import router as analytics_router
from app.ingestion import start_background_worker, stop_background_worker

# Set up logging format
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Purplle Store Intelligence Ingestion API",
    description="Asynchronous ingestion backend for real-time customer tracking and analytics",
    version="1.0.0"
)

# Register routes
app.include_router(health_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing Store Intelligence API...")
    
    # 1. Initialize Database Tables
    try:
        async with engine.begin() as conn:
            logger.info("Creating database tables if they do not exist...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.critical(f"Database initialization failed: {e}", exc_info=True)
        
    # 2. Start Background Worker
    try:
        await start_background_worker()
    except Exception as e:
        logger.critical(f"Failed to start background ingestion worker: {e}", exc_info=True)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Store Intelligence API...")
    
    # 1. Stop Background Worker
    await stop_background_worker()
    
    # 2. Dispose of DB Connections
    await engine.dispose()
    logger.info("Database connection pools cleaned up. Shutdown complete.")
