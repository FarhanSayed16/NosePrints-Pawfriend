"""
Application configuration — loaded from environment variables.
Uses pydantic-settings for typed, validated config.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """All application settings, sourced from env vars or .env file."""

    # ── App ──
    APP_NAME: str = "NosePrints-Pawfriend"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # ── Database ──
    DATABASE_URL: str = "postgresql+asyncpg://noseprints:noseprints@localhost:5432/noseprints_db"
    # Sync URL variant for Alembic migrations
    DATABASE_URL_SYNC: str = "postgresql://noseprints:noseprints@localhost:5432/noseprints_db"

    # ── S3-compatible object storage ──
    S3_ENDPOINT_URL: Optional[str] = None  # e.g., https://s3.amazonaws.com or Cloudflare R2 endpoint
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_BUCKET_NAME: str = "noseprints-photos"
    S3_REGION: str = "auto"

    # ── ML Models ──
    NOSE_DETECTOR_MODEL_PATH: str = "models/nose_detector.onnx"
    EMBEDDING_MODEL_PATH: str = "models/embedding_model.onnx"
    EMBEDDING_DIMENSION: int = 512

    # ── Matching ──
    MATCH_THRESHOLD: float = 0.85  # Cosine similarity threshold — tuned via ROC curve
    TOP_K_MATCHES: int = 5  # Number of top candidates to return

    # ── Image Quality Thresholds ──
    MIN_SHARPNESS_SCORE: float = 100.0  # Laplacian variance minimum
    MIN_BRIGHTNESS: int = 40
    MAX_BRIGHTNESS: int = 220
    MIN_NOSE_COVERAGE: float = 0.15  # Nose bbox must fill ≥ 15% of frame

    # ── CORS ──
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",
        "https://pawfriend.in",
        "https://www.pawfriend.in",
    ]

    # ── JWT (for admin/staff auth) ──
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60 * 24  # 24 hours

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


# Singleton instance
settings = Settings()
