"""
Application configuration — loaded from environment variables.
Uses pydantic-settings for typed, validated config.
"""

from pydantic import field_validator, model_validator
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
    # True in production. Set false only on Windows if antivirus MITM breaks Supabase TLS.
    DATABASE_SSL_VERIFY: bool = True

    # ── S3-compatible object storage ──
    S3_ENDPOINT_URL: Optional[str] = None  # e.g., https://s3.amazonaws.com or Cloudflare R2 endpoint
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_BUCKET_NAME: str = "noseprints-photos"
    S3_REGION: str = "auto"
    # Browser-facing base (R2 public / custom domain). If unset, falls back to endpoint/bucket path.
    S3_PUBLIC_BASE_URL: Optional[str] = None

    # ── ML Models ──
    NOSE_DETECTOR_MODEL_PATH: str = "models/nose_detector.onnx"
    EMBEDDING_MODEL_PATH: str = "models/embedding_model.onnx"
    EMBEDDING_DIMENSION: int = 512
    DETECTOR_CONF_THRESHOLD: float = 0.35
    DETECTOR_RETRY_CONF_THRESHOLD: float = 0.20
    DETECTOR_CLOSEUP_PAD: float = 0.30
    # Accept for register/identify only if final YOLO conf is at least this (blocks weak false positives).
    DETECTOR_MIN_ACCEPT_CONF: float = 0.40

    # ── Matching (from ml/eval_results/embedding/metrics.txt, 17 Aug 2026) ──
    # Cosine vs 6,000-dog gallery. Placeholder 0.85 was far too high for this model.
    MATCH_THRESHOLD: float = 0.56  # T_high ~5% FAR ("likely")
    MATCH_THRESHOLD_LOW: float = 0.51  # T_low ~20% FAR ("possible")
    # G2: public demos — disable "possible" band; only ≥ MATCH_THRESHOLD_STRICT counts as a match.
    MATCH_STRICT_DEMO: bool = False
    MATCH_THRESHOLD_STRICT: float = 0.60
    # Staff queue: when True (or when MATCH_STRICT_DEMO), only "matched" / likely rows appear.
    MATCH_QUEUE_LIKELY_ONLY: bool = False
    LOST_STATUS_BOOST: float = 0.03  # added to cosine for ranking only, not displayed score
    TOP_K_MATCHES: int = 5  # Number of top candidates to return

    # ── Image Quality Thresholds ──
    MIN_SHARPNESS_SCORE: float = 70.0  # Laplacian variance; 100 was too harsh on phone JPEGs
    MIN_BRIGHTNESS: int = 40
    MAX_BRIGHTNESS: int = 220
    MIN_NOSE_COVERAGE: float = 0.15  # Nose bbox must fill ≥ 15% of frame

    # ── G1 nose-crop heuristics (junk / keyboard filters) ──
    NOSE_CROP_MIN_ASPECT: float = 0.55
    NOSE_CROP_MAX_ASPECT: float = 1.85
    NOSE_MAX_EDGE_DENSITY: float = 0.22
    NOSE_MAX_GRID_REGULARITY: float = 0.42
    NOSE_MIN_LIKENESS: float = 0.32
    NOSE_MIN_LAPLACIAN: float = 28.0  # blank walls / flat fills
    NOSE_MAX_BBOX_FRAME_FRACTION: float = 0.92
    NOSE_MIN_BBOX_IN_CROP: float = 0.12
    # When True, run YOLO again on the cropped JPEG (G1.1).
    NOSE_REDETECT_ON_CROP: bool = True

    # ── G3 look-photo soft gate (full body / face — not biometric) ──
    # ── G3 look-photo soft gate ──
    LOOK_MAX_EDGE_DENSITY: float = 0.18
    LOOK_MAX_GRID_REGULARITY: float = 0.38
    LOOK_MIN_LAPLACIAN: float = 22.0
    # Public profile-photo overwrite window (hours after dog.created_at); staff bypasses
    PROFILE_PHOTO_OPEN_HOURS: int = 48

    # ── CORS (JSON list or comma-separated in env) ──
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://pawfriend.in",
        "https://www.pawfriend.in",
    ]

    # ── Deploy ──
    SERVE_FRONTEND: bool = False
    FRONTEND_DIR: str = "frontend_dist"

    # ── JWT (for admin/staff auth) ──
    JWT_SECRET_KEY: str = "dev-only-not-for-production-change-me-32b"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60 * 24  # 24 hours

    # ── Staff bootstrap (optional; only used if staff table is empty) ──
    STAFF_BOOTSTRAP_EMAIL: Optional[str] = None
    STAFF_BOOTSTRAP_PASSWORD: Optional[str] = None

    # ── Rate limits (per client IP, sliding 60s window) ──
    RATE_LIMIT_IDENTIFY_PER_MINUTE: int = 20
    RATE_LIMIT_UPLOAD_PER_MINUTE: int = 30
    RATE_LIMIT_FOUND_INTAKE_PER_MINUTE: int = 10

    # ── Email (optional; confirmed-match owner notify) ──
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None
    SMTP_USE_TLS: bool = True

    # ── Consent ──
    CONSENT_TEXT_VERSION: str = "v1"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            raw = value.strip()
            if raw.startswith("["):
                import json

                return json.loads(raw)
            return [part.strip() for part in raw.split(",") if part.strip()]
        return value

    @model_validator(mode="after")
    def normalize_database_urls(self):
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = "postgresql+asyncpg://" + url[len("postgres://") :]
        elif url.startswith("postgresql://") and "+asyncpg" not in url:
            url = "postgresql+asyncpg://" + url[len("postgresql://") :]
        self.DATABASE_URL = url
        self.DATABASE_URL_SYNC = url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return self

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        # POSTGRES_* in .env are for docker-compose only; app uses DATABASE_URL
        "extra": "ignore",
    }


# Singleton instance
settings = Settings()
