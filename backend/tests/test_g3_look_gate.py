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
    assert "keyboard" in joined or "grid" in joined or "edges" in joined or "busy" in joined


def test_blank_wall_look_soft_warns(fixtures):
    result = assess_look_photo(fixtures["blank_wall"].read_bytes())
    assert result.ok is True
    assert result.soft_warn is True
    joined = " ".join(result.issues).lower()
    assert "blank" in joined or "flat" in joined


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
