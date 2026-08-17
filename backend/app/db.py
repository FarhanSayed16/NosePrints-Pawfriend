"""
Async database session management using SQLAlchemy 2.0.
Provides the async engine, session factory, and dependency injection.
"""

from sqlalchemy import text
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
    from app.models.database import Base  # noqa: F401 — registers all tables

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        # Additive column for existing local DBs created before Phase 0
        await conn.execute(
            text(
                "ALTER TABLE owners "
                "ADD COLUMN IF NOT EXISTS consent_text_version VARCHAR(32) NOT NULL DEFAULT 'v1'"
            )
        )
