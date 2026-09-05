"""P2.9 — lightweight HTTP tests for look-check (no DB lifespan)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.dogs import router as dogs_router
from tests.fixtures_gen import ensure_fixtures


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(dogs_router, prefix="/api/v1")
    return TestClient(app)


def test_look_check_keyboard_soft_warns():
    fixtures = ensure_fixtures()
    data = fixtures["keyboard"].read_bytes()
    res = _client().post(
        "/api/v1/dogs/look-check",
        files={"file": ("keyboard.jpg", data, "image/jpeg")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["soft_warn"] is True
    assert body["issues"]


def test_look_check_blank_soft_warns():
    fixtures = ensure_fixtures()
    data = fixtures["blank_wall"].read_bytes()
    res = _client().post(
        "/api/v1/dogs/look-check",
        files={"file": ("blank.jpg", data, "image/jpeg")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["soft_warn"] is True


def test_dog_update_blank_breed_becomes_unknown():
    from app.schemas import DogUpdate

    upd = DogUpdate(breed="", color="  ")
    assert upd.breed == "Unknown"
    assert upd.color == "Unknown"
    # Omitted fields stay None (PATCH leave unchanged)
    partial = DogUpdate(name="Rex")
    assert partial.breed is None
    assert partial.color is None
