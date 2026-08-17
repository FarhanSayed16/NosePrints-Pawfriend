"""
Vector similarity matching service — the heart of dog identification.
Uses pgvector's cosine similarity to find the closest stored embeddings.
"""

import uuid
from datetime import datetime, timezone

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

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
    top_k: int | None = None,
) -> MatchResponse:
    """
    Search the database for dogs matching a query nose-print embedding.

    Uses pgvector's cosine distance operator (<=>) to find the closest
    stored embeddings, then applies a threshold to determine if any
    match is strong enough.

    Args:
        db: Async database session
        query_embedding: 512-d L2-normalized embedding vector
        quality_result: Image quality assessment result
        query_image_url: URL of the query image in storage
        top_k: Number of top candidates to return (default from settings)

    Returns:
        MatchResponse with candidates, scores, and match decision
    """
    if top_k is None:
        top_k = settings.TOP_K_MATCHES

    # Convert numpy array to list for pgvector
    embedding_list = query_embedding.tolist()

    # ── pgvector cosine similarity search ──
    # The <=> operator computes cosine DISTANCE (1 - similarity),
    # so we sort ascending and convert back to similarity score.
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
            d.profile_photo_url,
            o.name AS owner_name
        FROM nose_prints np
        JOIN dogs d ON np.dog_id = d.id
        LEFT JOIN owners o ON d.owner_id = o.id
        ORDER BY np.embedding <=> :query_vec ASC
        LIMIT :top_k
    """)

    result = await db.execute(
        query,
        {"query_vec": str(embedding_list), "top_k": top_k},
    )
    rows = result.fetchall()

    # ── Build candidates ──
    candidates: list[MatchCandidate] = []
    seen_dogs: set[str] = set()  # Deduplicate by dog_id (best score wins)

    for row in rows:
        dog_id_str = str(row.dog_id)
        if dog_id_str in seen_dogs:
            continue  # Already have a better-scoring embedding for this dog
        seen_dogs.add(dog_id_str)

        candidates.append(
            MatchCandidate(
                dog_id=row.dog_id,
                dog_name=row.dog_name,
                breed=row.breed,
                color=row.color,
                similarity_score=round(float(row.similarity_score), 4),
                matched_image_url=row.image_url,
                profile_photo_url=row.profile_photo_url,
                owner_name=row.owner_name,
                status=row.status,
            )
        )

    # ── Threshold decision ──
    top_score = candidates[0].similarity_score if candidates else 0.0
    match_found = top_score >= settings.MATCH_THRESHOLD

    # ── Log this match attempt (audit trail) ──
    match_log = MatchLog(
        query_image_url=query_image_url,
        top_match_dog_id=candidates[0].dog_id if candidates else None,
        top_match_score=top_score,
        result_status="matched" if match_found else "no_match",
    )
    db.add(match_log)
    await db.flush()  # Get the generated ID

    logger.info(
        f"Match search: top_score={top_score:.4f}, "
        f"threshold={settings.MATCH_THRESHOLD}, "
        f"match_found={match_found}, "
        f"candidates={len(candidates)}"
    )

    return MatchResponse(
        match_found=match_found,
        top_score=round(top_score, 4),
        threshold_used=settings.MATCH_THRESHOLD,
        candidates=candidates,
        query_image_url=query_image_url,
        quality_check=quality_result,
        match_log_id=match_log.id,
    )


async def confirm_match(
    db: AsyncSession,
    match_log_id: uuid.UUID,
    confirmed: bool,
    confirmed_by: uuid.UUID,
) -> dict:
    """
    Staff confirms or rejects a match — required before owner contact is released.

    Args:
        db: Async database session
        match_log_id: ID of the match log entry
        confirmed: Whether staff confirms the match
        confirmed_by: UUID of the staff member

    Returns:
        Updated match log status
    """
    result = await db.execute(
        select(MatchLog).where(MatchLog.id == match_log_id)
    )
    match_log = result.scalar_one_or_none()

    if not match_log:
        raise ValueError(f"Match log {match_log_id} not found")

    match_log.confirmed_by = confirmed_by
    match_log.confirmed_at = datetime.now(timezone.utc)
    match_log.result_status = "matched" if confirmed else "false_positive"

    return {
        "match_log_id": str(match_log.id),
        "confirmed": confirmed,
        "result_status": match_log.result_status,
    }
