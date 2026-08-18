"""Appearance histogram is a staff hint, not identity."""

import numpy as np

from app.services.appearance import appearance_hint, appearance_similarity, appearance_vector


def test_identical_images_score_high():
    import cv2

    img = np.zeros((80, 80, 3), dtype=np.uint8)
    img[:, :] = (40, 80, 160)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    raw = buf.tobytes()
    vec = appearance_vector(raw)
    assert vec is not None
    assert appearance_similarity(vec, vec) > 0.99
    assert appearance_hint(0.9) == "supports"
    assert appearance_hint(0.2) == "conflicts"
    assert appearance_hint(None) == "unavailable"
