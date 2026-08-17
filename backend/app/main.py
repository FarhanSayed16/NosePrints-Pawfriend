"""
NosePrints × PawFriend — FastAPI Application Entry Point

Dog biometric identification system using nose-print recognition.
Integrates with pawfriend.in as a lightweight PWA service.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, text

from app.config import settings
from app.routers import (
    auth_router,
    dogs_router,
    matching_router,
    noseprints_router,
    owners_router,
    registration_router,
)
from app.schemas import HealthResponse
from app.services import embedding_extractor, nose_detector, storage_service
from app.services.auth import hash_password, jwt_secret_is_unsafe

# ── Logging ──
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def _enforce_production_secrets() -> None:
    if settings.DEBUG:
        if jwt_secret_is_unsafe(settings.JWT_SECRET_KEY):
            logger.warning(
                "JWT_SECRET_KEY is a development default. Set a strong secret before production."
            )
        return
    if jwt_secret_is_unsafe(settings.JWT_SECRET_KEY):
        raise RuntimeError(
            "JWT_SECRET_KEY must be a strong unique secret (32+ chars) when DEBUG=false. "
            "Do not use the example value from .env.example."
        )


async def _bootstrap_staff_from_env() -> None:
    email = (settings.STAFF_BOOTSTRAP_EMAIL or "").strip().lower()
    password = settings.STAFF_BOOTSTRAP_PASSWORD or ""
    if not email or not password:
        return

    from app.db import async_session_factory
    from app.models.database import StaffUser

    async with async_session_factory() as session:
        count = await session.scalar(select(func.count()).select_from(StaffUser))
        if count and count > 0:
            return
        session.add(
            StaffUser(
                email=email,
                password_hash=hash_password(password),
                role="admin",
            )
        )
        await session.commit()
        logger.info("Bootstrapped first staff admin from STAFF_BOOTSTRAP_EMAIL")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup/shutdown lifecycle.
    Loads ML models and initializes services on startup.
    """
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    _enforce_production_secrets()

    nose_detector.load()
    embedding_extractor.load()
    storage_service.init()

    if settings.DEBUG:
        try:
            from app.db import init_db

            await init_db()
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.warning(f"Database init skipped (OK if using Alembic): {e}")

    try:
        await _bootstrap_staff_from_env()
    except Exception as e:
        logger.warning(f"Staff bootstrap skipped: {e}")

    if not settings.DEBUG and not embedding_extractor.is_loaded:
        logger.warning(
            "DEBUG=false but embedding ONNX is missing — identify/upload will return 503"
        )

    logger.info("All services initialized ✓")

    yield

    logger.info("Shutting down...")


# ── FastAPI App ──
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Dog biometric identification using nose-print recognition. "
        "A lightweight, web-integrated system for PawFriend.in to register dogs, "
        "reunite lost pets with owners, and identify found strays."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (for local dev uploads) ──
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ── API Routes ──
API_PREFIX = "/api/v1"
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(registration_router, prefix=API_PREFIX)
app.include_router(owners_router, prefix=API_PREFIX)
app.include_router(dogs_router, prefix=API_PREFIX)
app.include_router(noseprints_router, prefix=API_PREFIX)
app.include_router(matching_router, prefix=API_PREFIX)


def _embedding_mode() -> str:
    if embedding_extractor.is_loaded:
        return "real"
    if settings.DEBUG:
        return "placeholder"
    return "unavailable"


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check — real DB ping and model file presence."""
    from app.db import async_session_factory

    db_status = "disconnected"
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.warning(f"Health DB ping failed: {e}")
        db_status = "disconnected"

    detector_path = Path(settings.NOSE_DETECTOR_MODEL_PATH)
    embedding_path = Path(settings.EMBEDDING_MODEL_PATH)

    overall = "healthy" if db_status == "connected" else "degraded"

    return HealthResponse(
        status=overall,
        version=settings.APP_VERSION,
        database=db_status,
        ml_models={
            "nose_detector_loaded": nose_detector.is_loaded,
            "nose_detector_file": detector_path.exists(),
            "embedding_extractor_loaded": embedding_extractor.is_loaded,
            "embedding_extractor_file": embedding_path.exists(),
            "embedding_mode": _embedding_mode(),
        },
    )


@app.get("/", tags=["System"])
async def root():
    """Root endpoint — basic info."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
        "api": f"{API_PREFIX}/",
    }
