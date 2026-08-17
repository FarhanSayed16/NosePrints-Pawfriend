"""
Async database session management using SQLAlchemy 2.0.
Provides the async engine, session factory, and dependency injection.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings

# Async engine — connection pool for PostgreSQL
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Detect stale connections
)

# Session factory — creates new sessions per request
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """
    FastAPI dependency — yields an async database session.
    Automatically commits on success, rolls back on exception.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    Create all tables on startup (dev only).
    In production, use Alembic migrations instead.
    """
    from app.models.database import Base

    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
