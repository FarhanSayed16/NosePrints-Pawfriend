"""
Async database session management using SQLAlchemy 2.0.
Provides the async engine, session factory, and dependency injection.
"""

import ssl

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings


def _ssl_connect_args() -> dict:
    db_url = settings.DATABASE_URL
    if "localhost" in db_url or "127.0.0.1" in db_url:
        return {}
    if settings.DATABASE_SSL_VERIFY:
        try:
            import certifi

            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ctx = True
        return {"ssl": ctx}
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return {"ssl": ctx}


_db_url = settings.DATABASE_URL
engine = create_async_engine(
    _db_url,
    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args=_ssl_connect_args(),
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
        await conn.execute(
            text("ALTER TABLE dogs ADD COLUMN IF NOT EXISTS last_seen_note TEXT")
        )
        await conn.execute(
            text("ALTER TABLE dogs ADD COLUMN IF NOT EXISTS found_notes TEXT")
        )
        await conn.execute(
            text(
                "ALTER TABLE dogs ADD COLUMN IF NOT EXISTS listed_as_found_at TIMESTAMPTZ"
            )
        )
        await conn.execute(
            text("ALTER TABLE match_logs ADD COLUMN IF NOT EXISTS staff_notes TEXT")
        )
        await conn.execute(
            text(
                "ALTER TABLE match_logs "
                "ADD COLUMN IF NOT EXISTS query_appearance_url TEXT"
            )
        )
