"""
NosePrints × PawFriend — FastAPI Application Entry Point

Dog biometric identification system using nose-print recognition.
Integrates with pawfriend.in as a lightweight PWA service.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.routers import dogs_router, matching_router, noseprints_router, owners_router
from app.schemas import HealthResponse
from app.services import embedding_extractor, nose_detector, storage_service

# ── Logging ──
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup/shutdown lifecycle.
    Loads ML models and initializes services on startup.
    """
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Initialize services
    nose_detector.load()
    embedding_extractor.load()
    storage_service.init()

    # Create database tables (dev only — use Alembic in production)
    if settings.DEBUG:
        try:
            from app.db import init_db
            await init_db()
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.warning(f"Database init skipped (OK if using Alembic): {e}")

    logger.info("All services initialized ✓")

    yield  # Application runs here

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
app.include_router(owners_router, prefix=API_PREFIX)
app.include_router(dogs_router, prefix=API_PREFIX)
app.include_router(noseprints_router, prefix=API_PREFIX)
app.include_router(matching_router, prefix=API_PREFIX)


# ── Health Check ──
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint — reports service status and model availability."""
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        database="connected",  # TODO: actual DB ping
        ml_models={
            "nose_detector": nose_detector.is_loaded,
            "embedding_extractor": embedding_extractor.is_loaded,
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
