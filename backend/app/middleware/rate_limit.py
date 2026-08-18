"""In-memory sliding-window rate limit for public identify/upload paths."""

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings

WINDOW_SECONDS = 60


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def _limit_for(self, path: str, method: str) -> int | None:
        if method != "POST":
            return None
        if path == "/api/v1/match/identify":
            return settings.RATE_LIMIT_IDENTIFY_PER_MINUTE
        if path == "/api/v1/match/detect-preview":
            return settings.RATE_LIMIT_UPLOAD_PER_MINUTE
        if path.startswith("/api/v1/noseprints/upload"):
            return settings.RATE_LIMIT_UPLOAD_PER_MINUTE
        if "/profile-photo" in path:
            return settings.RATE_LIMIT_UPLOAD_PER_MINUTE
        if path in ("/api/v1/found-intake", "/api/v1/dogs/found-intake"):
            return settings.RATE_LIMIT_FOUND_INTAKE_PER_MINUTE
        return None

    def _bucket_path(self, path: str) -> str:
        if path.startswith("/api/v1/noseprints/upload"):
            return "/api/v1/noseprints/upload"
        return path

    async def dispatch(self, request: Request, call_next):
        limit = self._limit_for(request.url.path, request.method)
        if limit is None:
            return await call_next(request)

        key = (_client_ip(request), self._bucket_path(request.url.path))
        now = time.monotonic()
        window = self._hits[key]
        cutoff = now - WINDOW_SECONDS
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please wait a minute and try again."},
            )
        window.append(now)
        return await call_next(request)
