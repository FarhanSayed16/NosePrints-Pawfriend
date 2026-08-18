"""
Vector similarity matching service — the heart of dog identification.
Uses pgvector's cosine similarity to find the closest stored embeddings.
"""

import uuid
from datetime import datetime, timezone

import numpy as np
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import Dog, MatchLog, NosePrint, Owner
from app.schemas import MatchCandidate, MatchResponse, QualityCheckResult

import logging

logger = logging.getLogger(__name__)


async def find_matches(
    db: AsyncSession,
    query_embedding: np.ndarray,
    quality_result: QualityCheckResult,
    query_image_url: str | None = None,
    query_appearance_url: str | None = None,
    query_appearance_bytes: bytes | None = None,
    top_k: int | None = None,
) -> MatchResponse:
    """
    Search the database for dogs matching a query nose-print embedding.

    Appearance histogram is an optional staff hint only. It never decides match_found.
    """
    if top_k is None:
        top_k = settings.TOP_K_MATCHES

    embedding_list = query_embedding.tolist()
    fetch_k = max(top_k * 10, 30)

    query = text("""
        SELECT
            np.id AS noseprint_id,
            np.dog_id,
            np.image_url,
            1 - (np.embedding <=> :query_vec) AS similarity_score,
            d.name AS dog_name,
            d.breed,
            d.color,
            d.status,
            d.profile_photo_url
        FROM nose_prints np
        JOIN dogs d ON np.dog_id = d.id
        ORDER BY np.embedding <=> :query_vec ASC
        LIMIT :fetch_k
    """)

    result = await db.execute(
        query,
        {"query_vec": str(embedding_list), "fetch_k": fetch_k},
    )
    rows = result.fetchall()

    from app.services.appearance import (
        appearance_hint,
        appearance_similarity,
        appearance_vector,
    )
    from app.services.storage import storage_service

    query_vec = appearance_vector(query_appearance_bytes) if query_appearance_bytes else None
    profile_cache: dict[str, np.ndarray | None] = {}

    async def score_appearance(profile_url: str | None) -> tuple[float | None, str]:
        if query_vec is None or not profile_url:
            return None, "unavailable"
        if profile_url not in profile_cache:
            raw = await storage_service.read_image(profile_url)
            profile_cache[profile_url] = appearance_vector(raw) if raw else None
        gallery_vec = profile_cache[profile_url]
        if gallery_vec is None:
            return None, "unavailable"
        score = round(appearance_similarity(query_vec, gallery_vec), 4)
        return score, appearance_hint(score)

    candidates: list[MatchCandidate] = []
    seen_dogs: set[str] = set()

    for row in rows:
        dog_id_str = str(row.dog_id)
        if dog_id_str in seen_dogs:
            continue
        seen_dogs.add(dog_id_str)
        app_score, app_hint = await score_appearance(row.profile_photo_url)
        candidates.append(
            MatchCandidate(
                dog_id=row.dog_id,
                dog_name=row.dog_name,
                breed=row.breed,
                color=row.color,
                similarity_score=round(float(row.similarity_score), 4),
                matched_image_url=row.image_url,
                profile_photo_url=row.profile_photo_url,
                status=row.status,
                appearance_score=app_score,
                appearance_hint=app_hint,
            )
        )

    # Lost dogs get a ranking boost only — displayed score stays raw cosine.
    boost = settings.LOST_STATUS_BOOST
    candidates.sort(
        key=lambda c: (
            c.similarity_score + (boost if c.status == "lost" else 0.0),
            c.similarity_score,
        ),
        reverse=True,
    )
    candidates = candidates[:top_k]

    # ── Threshold decision (two-band, from ROC) ──
    top_score = candidates[0].similarity_score if candidates else 0.0
    t_high = settings.MATCH_THRESHOLD
    t_low = settings.MATCH_THRESHOLD_LOW
    if top_score >= t_high:
        confidence_band = "likely"
        match_found = True
        result_status = "matched"
    elif top_score >= t_low:
        confidence_band = "possible"
        match_found = True
        result_status = "possible_match"
    else:
        confidence_band = "none"
        match_found = False
        result_status = "no_match"

    # ── Log this match attempt (audit trail) ──
    match_log = MatchLog(
        query_image_url=query_image_url,
        query_appearance_url=query_appearance_url,
        top_match_dog_id=candidates[0].dog_id if candidates else None,
        top_match_score=top_score,
        result_status=result_status,
    )
    db.add(match_log)
    await db.flush()  # Get the generated ID

    logger.info(
        f"Match search: top_score={top_score:.4f}, "
        f"band={confidence_band}, "
        f"match_found={match_found}, "
        f"candidates={len(candidates)}"
    )

    return MatchResponse(
        match_found=match_found,
        confidence_band=confidence_band,
        top_score=round(top_score, 4),
        threshold_used=t_high if confidence_band == "likely" else t_low,
        candidates=candidates,
        query_image_url=query_image_url,
        query_appearance_url=query_appearance_url,
        quality_check=quality_result,
        match_log_id=match_log.id,
    )


async def confirm_match(
    db: AsyncSession,
    match_log_id: uuid.UUID,
    confirmed: bool,
    confirmed_by: uuid.UUID,
    staff_notes: str | None = None,
) -> dict:
    """
    Staff confirms or rejects a match — required before owner contact is released.

    Args:
        db: Async database session
        match_log_id: ID of the match log entry
        confirmed: Whether staff confirms the match
        confirmed_by: UUID of the staff member
        staff_notes: Optional review notes

    Returns:
        Updated match log status, plus owner contact only when confirmed
    """
    from app.schemas import DogResponse, OwnerResponse
    from app.services.notify import notify_owner_confirmed_match

    result = await db.execute(
        select(MatchLog).where(MatchLog.id == match_log_id)
    )
    match_log = result.scalar_one_or_none()

    if not match_log:
        raise ValueError(f"Match log {match_log_id} not found")

    match_log.confirmed_by = confirmed_by
    match_log.confirmed_at = datetime.now(timezone.utc)
    match_log.result_status = "matched" if confirmed else "false_positive"
    if staff_notes:
        match_log.staff_notes = staff_notes

    dog_payload = None
    owner_payload = None
    email_sent = False

    if confirmed and match_log.top_match_dog_id:
        dog_result = await db.execute(
            select(Dog).where(Dog.id == match_log.top_match_dog_id)
        )
        dog = dog_result.scalar_one_or_none()
        if dog:
            if dog.status == "lost":
                dog.status = "registered"
            count_result = await db.execute(
                select(func.count(NosePrint.id)).where(NosePrint.dog_id == dog.id)
            )
            count = count_result.scalar() or 0
            dog_payload = DogResponse(
                id=dog.id,
                owner_id=dog.owner_id,
                name=dog.name,
                breed=dog.breed,
                color=dog.color,
                sex=dog.sex,
                approx_dob=dog.approx_dob.date() if dog.approx_dob else None,
                microchip_id=dog.microchip_id,
                status=dog.status,
                last_seen_latitude=dog.last_seen_latitude,
                last_seen_longitude=dog.last_seen_longitude,
                last_seen_at=dog.last_seen_at,
                last_seen_note=dog.last_seen_note,
                found_notes=dog.found_notes,
                listed_as_found_at=dog.listed_as_found_at,
                profile_photo_url=dog.profile_photo_url,
                nose_print_count=count,
                created_at=dog.created_at,
            )
            if dog.owner_id:
                owner_result = await db.execute(
                    select(Owner).where(Owner.id == dog.owner_id)
                )
                owner = owner_result.scalar_one_or_none()
                if owner:
                    owner_payload = OwnerResponse.model_validate(owner)
                    email_sent = notify_owner_confirmed_match(owner.email, dog.name)

    return {
        "match_log_id": match_log.id,
        "confirmed": confirmed,
        "result_status": match_log.result_status,
        "email_sent": email_sent,
        "dog": dog_payload,
        "owner": owner_payload,
    }


async def list_match_queue(
    db: AsyncSession,
    include_reviewed: bool = False,
    page: int = 1,
    per_page: int = 20,
) -> list:
    """Staff match queue. Owner contact is never included here."""
    from app.schemas import MatchQueueItem

    pending = MatchLog.result_status.in_(("matched", "possible_match"))
    query = select(MatchLog, Dog).outerjoin(
        Dog, Dog.id == MatchLog.top_match_dog_id
    )
    if include_reviewed:
        query = query.where(pending | MatchLog.confirmed_at.is_not(None))
    else:
        query = query.where(pending, MatchLog.confirmed_at.is_(None))

    offset = (page - 1) * per_page
    query = query.order_by(MatchLog.created_at.desc()).offset(offset).limit(per_page)
    rows = (await db.execute(query)).all()

    items = []
    for match_log, dog in rows:
        matched_image_url = None
        if dog:
            np_result = await db.execute(
                select(NosePrint.image_url)
                .where(NosePrint.dog_id == dog.id)
                .order_by(NosePrint.is_primary.desc(), NosePrint.created_at.desc())
                .limit(1)
            )
            matched_image_url = np_result.scalar_one_or_none()

        items.append(
            MatchQueueItem(
                id=match_log.id,
                query_image_url=match_log.query_image_url,
                top_match_dog_id=match_log.top_match_dog_id,
                top_match_score=match_log.top_match_score,
                result_status=match_log.result_status,
                staff_notes=match_log.staff_notes,
                confirmed_at=match_log.confirmed_at,
                created_at=match_log.created_at,
                dog_name=dog.name if dog else None,
                breed=dog.breed if dog else None,
                color=dog.color if dog else None,
                status=dog.status if dog else None,
                matched_image_url=matched_image_url,
                profile_photo_url=dog.profile_photo_url if dog else None,
                query_appearance_url=match_log.query_appearance_url,
            )
        )
    return items

