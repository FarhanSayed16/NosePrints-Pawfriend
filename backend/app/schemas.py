"""
Pydantic schemas for request/response validation.
Separated from SQLAlchemy models for clean API boundaries.
"""

from datetime import datetime, date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr


# ────────────────────────────────────────────
# Owner Schemas
# ────────────────────────────────────────────

class OwnerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., min_length=10, max_length=15)
    email: Optional[str] = None
    address: Optional[str] = None


class OwnerResponse(BaseModel):
    id: UUID
    name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    consent_given_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class OwnerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    email: Optional[str] = None
    address: Optional[str] = None


# ────────────────────────────────────────────
# Dog Schemas
# ────────────────────────────────────────────

class DogCreate(BaseModel):
    owner_id: Optional[UUID] = None
    name: Optional[str] = Field(None, max_length=255)
    breed: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, max_length=100)
    sex: Optional[str] = Field(None, max_length=10)
    approx_dob: Optional[date] = None
    microchip_id: Optional[str] = Field(None, max_length=50)
    status: str = Field(default="registered", pattern="^(registered|lost|found)$")


class DogResponse(BaseModel):
    id: UUID
    owner_id: Optional[UUID] = None
    name: Optional[str] = None
    breed: Optional[str] = None
    color: Optional[str] = None
    sex: Optional[str] = None
    approx_dob: Optional[date] = None
    microchip_id: Optional[str] = None
    status: str
    last_seen_latitude: Optional[float] = None
    last_seen_longitude: Optional[float] = None
    last_seen_at: Optional[datetime] = None
    profile_photo_url: Optional[str] = None
    nose_print_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class DogUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    breed: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, max_length=100)
    sex: Optional[str] = Field(None, max_length=10)
    approx_dob: Optional[date] = None
    microchip_id: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, pattern="^(registered|lost|found)$")
    last_seen_latitude: Optional[float] = None
    last_seen_longitude: Optional[float] = None


class DogSearchParams(BaseModel):
    """Query parameters for searching / filtering dogs."""
    breed: Optional[str] = None
    color: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


# ────────────────────────────────────────────
# Nose Print Schemas
# ────────────────────────────────────────────

class NosePrintResponse(BaseModel):
    id: UUID
    dog_id: UUID
    image_url: str
    quality_score: Optional[float] = None
    is_primary: bool
    captured_at: datetime

    model_config = {"from_attributes": True}


class QualityCheckResult(BaseModel):
    """Result of image quality assessment."""
    passed: bool
    sharpness_score: float
    brightness_score: float
    nose_coverage: float
    issues: list[str] = []


# ────────────────────────────────────────────
# Match Schemas
# ────────────────────────────────────────────

class MatchCandidate(BaseModel):
    """A single candidate match from similarity search."""
    dog_id: UUID
    dog_name: Optional[str] = None
    breed: Optional[str] = None
    color: Optional[str] = None
    similarity_score: float
    matched_image_url: str
    profile_photo_url: Optional[str] = None
    owner_name: Optional[str] = None
    status: str


class MatchResponse(BaseModel):
    """Complete response from a nose-print matching attempt."""
    match_found: bool
    top_score: float
    threshold_used: float
    candidates: list[MatchCandidate] = []
    query_image_url: Optional[str] = None
    quality_check: QualityCheckResult
    match_log_id: UUID


class MatchConfirmation(BaseModel):
    """Staff confirmation of a match."""
    match_log_id: UUID
    confirmed: bool
    confirmed_by: UUID  # Staff member UUID


# ────────────────────────────────────────────
# Registration Flow (Combined)
# ────────────────────────────────────────────

class RegistrationResponse(BaseModel):
    """Response after registering a dog with nose prints."""
    dog: DogResponse
    owner: Optional[OwnerResponse] = None
    nose_prints: list[NosePrintResponse] = []
    message: str = "Dog registered successfully"


# ────────────────────────────────────────────
# Health / Info
# ────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    ml_models: dict[str, bool]
