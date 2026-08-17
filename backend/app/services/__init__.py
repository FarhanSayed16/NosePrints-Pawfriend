"""Service package. Heavy modules (DB, S3) load lazily so detector unit tests stay light."""

from .embedding import EmbeddingExtractor, embedding_extractor
from .nose_detector import DetectionResult, NoseDetector, nose_detector
from .quality import assess_crop_quality, assess_image_quality

__all__ = [
    "assess_image_quality",
    "assess_crop_quality",
    "nose_detector",
    "NoseDetector",
    "DetectionResult",
    "embedding_extractor",
    "EmbeddingExtractor",
    "find_matches",
    "confirm_match",
    "storage_service",
    "StorageService",
    "require_embedding_model",
    "prepare_nose_scan",
]


def __getattr__(name: str):
    if name in {"find_matches", "confirm_match"}:
        from .matcher import confirm_match, find_matches

        return find_matches if name == "find_matches" else confirm_match
    if name in {"storage_service", "StorageService"}:
        from .storage import StorageService, storage_service

        return storage_service if name == "storage_service" else StorageService
    if name == "require_embedding_model":
        from .ml_guard import require_embedding_model

        return require_embedding_model
    if name == "prepare_nose_scan":
        from .capture_pipeline import prepare_nose_scan

        return prepare_nose_scan
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
