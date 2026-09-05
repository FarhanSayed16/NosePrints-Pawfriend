"""Rules for which photo URLs we will read or delete."""

from urllib.parse import urlparse


def is_trusted_media_url(
    url: str | None,
    *,
    bucket: str | None = None,
    public_base: str | None = None,
) -> bool:
    """Only our stored objects — never fetch arbitrary URLs."""
    if not url:
        return False
    if url.startswith("/uploads/") and ".." not in url:
        return True
    if not url.startswith("https://"):
        return False
    base = (public_base or "").rstrip("/")
    if base and url.startswith(base + "/"):
        return ".." not in url
    if bucket and bucket in url:
        return True
    # Path-style API URL without matching public_base
    path = urlparse(url).path
    return bool(bucket and f"/{bucket}/" in path)
