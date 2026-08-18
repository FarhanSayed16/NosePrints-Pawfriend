"""
Coat / body appearance helper — NOT a biometric.

HSV histogram correlation is a staff hint so a brown dog is less likely
to be confirmed against a white-dog profile. Nose cosine remains the ID.
"""

import cv2
import numpy as np


def appearance_vector(image_bytes: bytes) -> np.ndarray | None:
    if not image_bytes:
        return None
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None or img.size == 0:
        return None
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist(
        [hsv],
        [0, 1, 2],
        None,
        [16, 8, 8],
        [0, 180, 0, 256, 0, 256],
    )
    vec = hist.flatten().astype(np.float64)
    n = float(np.linalg.norm(vec))
    if n < 1e-9:
        return None
    return vec / n


def appearance_similarity(query: np.ndarray, gallery: np.ndarray) -> float:
    return float(np.clip(np.dot(query, gallery), 0.0, 1.0))


def appearance_hint(score: float | None) -> str:
    if score is None:
        return "unavailable"
    if score >= 0.72:
        return "supports"
    if score < 0.42:
        return "conflicts"
    return "unclear"
