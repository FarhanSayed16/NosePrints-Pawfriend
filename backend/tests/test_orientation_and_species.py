"""EXIF/rotation mapping + human-skin rejection for nose crops."""

import cv2
import numpy as np

from app.services.image_io import map_bbox_from_rotated, rotate_bgr
from app.services.nose_heuristics import assess_nose_crop_heuristics, human_skin_score


def test_map_bbox_roundtrip_rotations():
    """A painted box survives 90/180/270 detect→map-back."""
    h, w = 200, 300
    img = np.zeros((h, w, 3), dtype=np.uint8)
    box = (100, 60, 160, 120)
    cv2.rectangle(img, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), -1)

    for angle in (0, 90, 180, 270):
        rot = rotate_bgr(img, angle)
        # Find red blob on rotated canvas
        mask = rot[:, :, 2] > 200
        ys, xs = np.where(mask)
        rb = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
        mapped = map_bbox_from_rotated(
            rb, angle_cw=angle, orig_w=w, orig_h=h
        )
        assert mapped is not None
        mx1, my1, mx2, my2 = mapped
        # Overlap with original box should be high
        ix1, iy1 = max(box[0], mx1), max(box[1], my1)
        ix2, iy2 = min(box[2], mx2), min(box[3], my2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        area = (box[2] - box[0]) * (box[3] - box[1])
        assert inter / area > 0.7, f"angle={angle} mapped={mapped} box={box}"


def test_human_skin_crop_rejected():
    """Peach skin fill must not pass as a dog nose print."""
    size = 160
    # Smooth peach skin (BGR)
    img = np.full((size, size, 3), (140, 170, 210), dtype=np.uint8)
    rng = np.random.default_rng(7)
    noise = rng.integers(0, 8, img.shape, dtype=np.uint8)
    img = cv2.add(img, noise)
    # Mild darker nostrils (still skin-like, not black leather)
    cv2.ellipse(img, (70, 90), (12, 8), 0, 0, 360, (100, 130, 170), -1)
    cv2.ellipse(img, (95, 90), (12, 8), 0, 0, 360, (100, 130, 170), -1)

    assert human_skin_score(img) >= 0.35
    result = assess_nose_crop_heuristics(img, pre_cropped=True)
    assert result.passed is False
    joined = " ".join(result.issues).lower()
    assert "human" in joined or "skin" in joined or "leather" in joined


def test_black_dog_nose_not_flagged_as_human():
    size = 160
    img = np.full((size, size, 3), (120, 130, 140), dtype=np.uint8)
    cv2.ellipse(img, (80, 80), (42, 38), 0, 0, 360, (18, 16, 14), -1)
    rng = np.random.default_rng(2)
    noise = rng.integers(0, 12, img.shape, dtype=np.uint8)
    img = cv2.add(img, noise // 2)
    # Black leather center must pass the gate even if border fur is tan
    result = assess_nose_crop_heuristics(img, pre_cropped=True)
    assert result.passed is True, result.issues
    assert result.scores.get("dark_center", 0) >= 0.40
    assert "human" not in " ".join(result.issues).lower()
