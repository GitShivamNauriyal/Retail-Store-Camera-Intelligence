import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from redis.asyncio import Redis

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://purplle_admin:purplle_secure_pass@127.0.0.1:5433/store_intelligence"
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Async Engine and Session Maker
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Dependency for DB Session
async def get_db():
    async with async_session() as session:
        yield session

# Helper to get Redis client
def get_redis_client() -> Redis:
    return Redis.from_url(REDIS_URL, decode_responses=True)
