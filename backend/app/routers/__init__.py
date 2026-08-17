from .owners import router as owners_router
from .dogs import router as dogs_router
from .noseprints import router as noseprints_router
from .matching import router as matching_router
from .auth import router as auth_router
from .registration import router as registration_router

__all__ = [
    "owners_router",
    "dogs_router",
    "noseprints_router",
    "matching_router",
    "auth_router",
    "registration_router",
]
