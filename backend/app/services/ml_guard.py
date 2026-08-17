"""
Refuse placeholder biometric matching outside debug mode.
"""

from fastapi import HTTPException, status

from app.config import settings
from app.services.embedding import embedding_extractor


def require_embedding_model() -> None:
    """
    Real identification needs a loaded ONNX embedding model.
    Placeholder vectors are allowed only when DEBUG=true.
    """
    if embedding_extractor.is_loaded:
        return
    if settings.DEBUG:
        return
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=(
            "Nose-print matching is unavailable: the embedding model is not loaded. "
            "Placeholder matching is disabled when DEBUG=false."
        ),
    )
