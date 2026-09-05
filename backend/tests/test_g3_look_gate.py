"""G3 look-photo soft gate + breed/color Unknown normalization."""

import pytest

from app.schemas import DogCreate, FoundIntakeRequest
from app.services.look_gate import assess_look_photo
from tests.fixtures_gen import ensure_fixtures


@pytest.fixture(scope="module")
def fixtures():
    return ensure_fixtures()


def test_keyboard_look_soft_warns(fixtures):
    result = assess_look_photo(fixtures["keyboard"].read_bytes())
    assert result.ok is True
    assert result.soft_warn is True
    joined = " ".join(result.issues).lower()
    assert "keyboard" in joined or "grid" in joined or "edges" in joined or "busy" in joined or "screen" in joined


def test_blank_wall_look_soft_warns(fixtures):
    result = assess_look_photo(fixtures["blank_wall"].read_bytes())
    assert result.ok is True
    assert result.soft_warn is True
    joined = " ".join(result.issues).lower()
    assert "blank" in joined or "flat" in joined


def test_chat_screen_look_soft_warns():
    """Synthetic WhatsApp-like green bubbles should soft-warn (not Photo ready)."""
    import cv2
    import numpy as np

    img = np.full((320, 240, 3), 40, dtype=np.uint8)
    # green chat bubbles (BGR)
    cv2.rectangle(img, (20, 40), (200, 90), (80, 200, 90), -1)
    cv2.rectangle(img, (40, 120), (220, 170), (80, 200, 90), -1)
    cv2.rectangle(img, (20, 200), (180, 250), (80, 200, 90), -1)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    result = assess_look_photo(buf.tobytes())
    assert result.ok is True
    assert result.soft_warn is True
    assert result.scores.get("screen_ui_score", 0) >= 0.35 or any(
        "screen" in i.lower() or "busy" in i.lower() or "edges" in i.lower() for i in result.issues
    )


def test_tiny_look_hard_rejects():
    # Minimal valid JPEG that decodes tiny — use a 1x1 png via opencv-written jpeg path
    import cv2
    import numpy as np

    tiny = np.zeros((32, 32, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", tiny)
    assert ok
    result = assess_look_photo(buf.tobytes())
    assert result.ok is False
    assert result.soft_warn is False


def test_dog_create_blank_breed_color_become_unknown():
    dog = DogCreate(breed="", color="  ")
    assert dog.breed == "Unknown"
    assert dog.color == "Unknown"


def test_dog_create_none_breed_color_become_unknown():
    dog = DogCreate()
    assert dog.breed == "Unknown"
    assert dog.color == "Unknown"


def test_found_intake_blank_labels():
    req = FoundIntakeRequest(breed="", color=None)
    assert req.breed == "Unknown"
    assert req.color == "Unknown"
