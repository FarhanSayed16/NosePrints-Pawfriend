"""Trust checks for stored media URLs (no network)."""

from app.services.media_urls import is_trusted_media_url


def test_trusted_local_upload_path():
    assert is_trusted_media_url("/uploads/match-queries/abc.jpg")
    assert not is_trusted_media_url("/uploads/../etc/passwd")
    assert not is_trusted_media_url("https://evil.example/photo.jpg")
    assert not is_trusted_media_url("")
    assert not is_trusted_media_url(None)


def test_trusted_https_bucket_url():
    assert is_trusted_media_url(
        "https://s3.example/noseprints-photos/x.jpg",
        bucket="noseprints-photos",
    )
    assert not is_trusted_media_url(
        "http://s3.example/noseprints-photos/x.jpg",
        bucket="noseprints-photos",
    )
