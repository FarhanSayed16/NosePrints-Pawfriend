"""
SQLAlchemy database models — the core data layer.

Schema:
- owners: Dog owner contact information (DPDP Act compliant)
- dogs: Dog profiles with breed, color, status
- nose_prints: Biometric embeddings (pgvector) + photo references
- match_logs: Audit trail for all matching attempts
- staff_users: PawFriend staff accounts (JWT login)
"""

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Owner(Base):
    """
    Dog owner — stores contact information.
    DPDP Act 2023 compliance: consent_given_at is mandatory,
    and full data deletion must be supported on request.
    """
    __tablename__ = "owners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    phone = Column(String(15), nullable=False)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    consent_given_at = Column(DateTime(timezone=True), nullable=False)
    consent_text_version = Column(String(32), nullable=False, default="v1")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    dogs = relationship("Dog", back_populates="owner", cascade="all, delete-orphan")


class Dog(Base):
    """
    Dog profile — breed, color, status, and optional microchip.
    Status can be: registered, lost, found
    """
    __tablename__ = "dogs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("owners.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=True)
    breed = Column(String(100), nullable=True)
    color = Column(String(100), nullable=True)
    sex = Column(String(10), nullable=True)
    approx_dob = Column(DateTime, nullable=True)
    microchip_id = Column(String(50), nullable=True)
    status = Column(String(20), default="registered", nullable=False)  # registered / lost / found
    last_seen_latitude = Column(Float, nullable=True)
    last_seen_longitude = Column(Float, nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    profile_photo_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    owner = relationship("Owner", back_populates="dogs")
    nose_prints = relationship("NosePrint", back_populates="dog", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("ix_dogs_status", "status"),
        Index("ix_dogs_breed", "breed"),
    )


class NosePrint(Base):
    """
    Biometric nose print — stores the 512-d embedding vector (pgvector)
    and a reference URL to the original photo in S3 object storage.

    Multiple embeddings per dog (3–5) for better real-world recall
    across different angles and lighting conditions.
    """
    __tablename__ = "nose_prints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dog_id = Column(UUID(as_uuid=True), ForeignKey("dogs.id", ondelete="CASCADE"), nullable=False)
    embedding = Column(Vector(512), nullable=False)  # pgvector 512-d
    image_url = Column(Text, nullable=False)  # S3 object URL
    quality_score = Column(Float, nullable=True)
    captured_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    dog = relationship("Dog", back_populates="nose_prints")

    # NOTE: HNSW index is created via raw SQL migration when embeddings exceed ~1000
    # CREATE INDEX ON nose_prints USING hnsw (embedding vector_cosine_ops)
    #     WITH (m = 16, ef_construction = 64);


class MatchLog(Base):
    """
    Audit trail — every matching attempt is logged for review,
    accuracy analysis, and debugging.
    """
    __tablename__ = "match_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_image_url = Column(Text, nullable=True)
    top_match_dog_id = Column(UUID(as_uuid=True), ForeignKey("dogs.id", ondelete="SET NULL"), nullable=True)
    top_match_score = Column(Float, nullable=True)
    confirmed_by = Column(UUID(as_uuid=True), nullable=True)  # Staff member UUID
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    result_status = Column(String(20), nullable=True)  # matched / no_match / false_positive
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    matched_dog = relationship("Dog", foreign_keys=[top_match_dog_id])


class StaffUser(Base):
    """PawFriend staff — required before owner contact is visible."""

    __tablename__ = "staff_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="staff")  # staff | admin
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
