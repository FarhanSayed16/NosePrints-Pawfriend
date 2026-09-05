"""
Pydantic schemas for request/response validation.
Separated from SQLAlchemy models for clean API boundaries.
"""

from datetime import datetime, date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ────────────────────────────────────────────
# Owner Schemas
# ────────────────────────────────────────────

class OwnerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    phone: str = Field(..., min_length=10, max_length=15)
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    consent: bool = Field(..., description="Must be true — DPDP Act explicit consent")

    @field_validator("email", mode="before")
    @classmethod
    def empty_email_to_none(cls, value):
        if value == "" or value is None:
            return None
        return value

    @field_validator("consent")
    @classmethod
    def consent_must_be_true(cls, value: bool) -> bool:
        if value is not True:
            raise ValueError("Explicit consent is required to register")
        return value


class OwnerResponse(BaseModel):
    id: UUID
    name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    consent_given_at: datetime
    consent_text_version: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OwnerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, min_length=10, max_length=15)
    email: Optional[EmailStr] = None
    address: Optional[str] = None

    @field_validator("email", mode="before")
    @classmethod
    def empty_email_to_none(cls, value):
        if value == "" or value is None:
            return None
        return value


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
    last_seen_note: Optional[str] = None
    found_notes: Optional[str] = None
    listed_as_found_at: Optional[datetime] = None
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
    last_seen_at: Optional[datetime] = None
    last_seen_note: Optional[str] = Field(None, max_length=500)
    found_notes: Optional[str] = Field(None, max_length=2000)


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

class BBoxNorm(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class DetectPreviewResponse(BaseModel):
    detected: bool
    confidence: float = 0.0
    image_width: int
    image_height: int
    bbox: Optional[BBoxNorm] = None
    message: str


class MatchCandidate(BaseModel):
    """Public candidate — never includes owner contact."""
    dog_id: UUID
    dog_name: Optional[str] = None
    breed: Optional[str] = None
    color: Optional[str] = None
    similarity_score: float
    matched_image_url: str
    profile_photo_url: Optional[str] = None
    status: str
    appearance_score: Optional[float] = None
    appearance_hint: str = "unavailable"


class MatchResponse(BaseModel):
    """Complete response from a nose-print matching attempt."""
    match_found: bool
    confidence_band: str = "none"  # likely | possible | none
    top_score: float
    threshold_used: float
    candidates: list[MatchCandidate] = []
    query_image_url: Optional[str] = None
    query_appearance_url: Optional[str] = None
    quality_check: QualityCheckResult
    match_log_id: UUID


class MatchConfirmation(BaseModel):
    """Staff confirmation of a match. confirmed_by comes from the JWT."""
    match_log_id: UUID
    confirmed: bool
    staff_notes: Optional[str] = Field(None, max_length=2000)


class MatchQueueItem(BaseModel):
    """Staff queue row — still no owner contact until confirm."""
    id: UUID
    query_image_url: Optional[str] = None
    top_match_dog_id: Optional[UUID] = None
    top_match_score: Optional[float] = None
    result_status: Optional[str] = None
    staff_notes: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    created_at: datetime
    dog_name: Optional[str] = None
    breed: Optional[str] = None
    color: Optional[str] = None
    status: Optional[str] = None
    matched_image_url: Optional[str] = None
    profile_photo_url: Optional[str] = None
    query_appearance_url: Optional[str] = None
    appearance_score: Optional[float] = None
    appearance_hint: str = "unavailable"


class MatchConfirmResponse(BaseModel):
    match_log_id: UUID
    confirmed: bool
    result_status: str
    email_sent: bool = False
    dog: Optional[DogResponse] = None
    owner: Optional[OwnerResponse] = None


class ReportLostRequest(BaseModel):
    last_seen_latitude: Optional[float] = None
    last_seen_longitude: Optional[float] = None
    last_seen_note: Optional[str] = Field(None, max_length=500)


class FoundIntakeRequest(BaseModel):
    finder_nickname: Optional[str] = Field(None, max_length=100)
    finder_phone: Optional[str] = Field(None, max_length=15)
    location_note: Optional[str] = Field(None, max_length=500)
    last_seen_latitude: Optional[float] = None
    last_seen_longitude: Optional[float] = None
    breed: Optional[str] = Field(None, max_length=100)
    color: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = Field(None, max_length=1000)
    query_image_url: Optional[str] = Field(
        None,
        max_length=500,
        description="Stored crop URL from identify (must be /uploads/...)",
    )


# ────────────────────────────────────────────
# Registration Flow (Combined)
# ────────────────────────────────────────────

class CombinedRegisterRequest(BaseModel):
    owner: OwnerCreate
    dog: DogCreate


class CombinedRegisterResponse(BaseModel):
    """Owner payload is returned only to the registering client (their own data)."""
    dog: DogResponse
    owner: OwnerResponse
    message: str = "Owner and dog registered successfully"


class RegistrationResponse(BaseModel):
    """Response after registering a dog with nose prints."""
    dog: DogResponse
    owner: Optional[OwnerResponse] = None
    nose_prints: list[NosePrintResponse] = []
    message: str = "Dog registered successfully"


# ────────────────────────────────────────────
# Staff Auth
# ────────────────────────────────────────────

class StaffLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)


class StaffTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    staff_id: UUID
    email: str
    role: str


class StaffMeResponse(BaseModel):
    staff_id: UUID
    email: str
    role: str


# ────────────────────────────────────────────
# Health / Info
# ────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    ml_models: dict[str, bool | str]
    storage: str = "local"
