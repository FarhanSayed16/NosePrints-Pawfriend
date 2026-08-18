"""Rules for which photo URLs we will read or delete."""


def is_trusted_media_url(url: str | None, *, bucket: str | None = None) -> bool:
    """Only our stored objects — never fetch arbitrary URLs."""
    if not url:
        return False
    if url.startswith("/uploads/") and ".." not in url:
        return True
    return bool(bucket and bucket in url and url.startswith("https://"))
