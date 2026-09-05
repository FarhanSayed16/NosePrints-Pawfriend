"""
S3-compatible object storage service.
Handles photo uploads to Cloudflare R2 / Backblaze B2 / AWS S3 / GCS (S3 API).
Falls back to local filesystem storage for development.
"""

import uuid
from pathlib import Path
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

from app.config import settings
from app.services.media_urls import is_trusted_media_url
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """
    Handles file uploads to S3-compatible storage.
    Falls back to local filesystem if S3 is not configured.
    """

    def __init__(self):
        self.s3_client = None
        self._use_local = False
        self._local_dir = Path("uploads")

    @property
    def mode(self) -> str:
        """Report backend for /health — local | s3."""
        if self._use_local or self.s3_client is None:
            return "local"
        return "s3"

    def init(self):
        """Initialize the storage backend. Called once at startup."""
        if settings.S3_ENDPOINT_URL and settings.S3_ACCESS_KEY:
            try:
                self.s3_client = boto3.client(
                    "s3",
                    endpoint_url=settings.S3_ENDPOINT_URL,
                    aws_access_key_id=settings.S3_ACCESS_KEY,
                    aws_secret_access_key=settings.S3_SECRET_KEY,
                    region_name=settings.S3_REGION,
                )
                public = (settings.S3_PUBLIC_BASE_URL or "").rstrip("/") or "(endpoint path-style)"
                logger.info(
                    "S3 storage initialized: endpoint=%s public=%s bucket=%s",
                    settings.S3_ENDPOINT_URL,
                    public,
                    settings.S3_BUCKET_NAME,
                )
            except Exception as e:
                logger.warning(f"S3 init failed, falling back to local: {e}")
                self._use_local = True
                self.s3_client = None
        else:
            logger.info("S3 not configured — using local filesystem storage")
            self._use_local = True

        if self._use_local:
            self._local_dir.mkdir(parents=True, exist_ok=True)

    def _public_url(self, key: str) -> str:
        """URL stored in DB / returned to browsers."""
        base = (settings.S3_PUBLIC_BASE_URL or "").rstrip("/")
        if base:
            return f"{base}/{key}"
        endpoint = (settings.S3_ENDPOINT_URL or "").rstrip("/")
        return f"{endpoint}/{settings.S3_BUCKET_NAME}/{key}"

    def _key_from_url(self, url: str) -> str | None:
        """Extract object key from a stored URL (public or path-style API)."""
        if not url:
            return None
        if url.startswith("/uploads/"):
            return url[len("/uploads/") :]
        bucket = settings.S3_BUCKET_NAME
        public = (settings.S3_PUBLIC_BASE_URL or "").rstrip("/")
        if public and url.startswith(public + "/"):
            return url[len(public) + 1 :]
        marker = f"/{bucket}/"
        if marker in url:
            return url.split(marker, 1)[-1]
        # Custom domain where path is the key only
        path = urlparse(url).path.lstrip("/")
        return path or None

    async def upload_image(
        self,
        image_bytes: bytes,
        folder: str = "nose-prints",
        content_type: str = "image/jpeg",
    ) -> str:
        """
        Upload an image and return its URL.

        Args:
            image_bytes: Raw image data
            folder: Subfolder/prefix in the bucket
            content_type: MIME type

        Returns:
            URL string to access the uploaded file
        """
        ext = "jpg" if "jpeg" in content_type else content_type.split("/")[-1]
        filename = f"{folder}/{uuid.uuid4()}.{ext}"

        if self._use_local:
            return await self._upload_local(image_bytes, filename)
        else:
            return await self._upload_s3(image_bytes, filename, content_type)

    async def _upload_s3(
        self, image_bytes: bytes, key: str, content_type: str
    ) -> str:
        """Upload to S3-compatible storage."""
        try:
            self.s3_client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=key,
                Body=image_bytes,
                ContentType=content_type,
            )
            url = self._public_url(key)
            logger.debug(f"Uploaded to S3: {url}")
            return url
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise

    async def _upload_local(self, image_bytes: bytes, filename: str) -> str:
        """Fallback: save to local filesystem."""
        filepath = self._local_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_bytes(image_bytes)
        url = f"/uploads/{filename}"
        logger.debug(f"Saved locally: {filepath}")
        return url

    def is_trusted_url(self, url: str | None) -> bool:
        return is_trusted_media_url(
            url,
            bucket=settings.S3_BUCKET_NAME,
            public_base=settings.S3_PUBLIC_BASE_URL,
        )

    def _local_path(self, url: str) -> Path:
        relative = url[len("/uploads/") :] if url.startswith("/uploads/") else url.lstrip("/")
        return self._local_dir / relative

    async def read_image(self, url: str) -> bytes | None:
        """Read bytes for a previously uploaded object. Returns None if untrusted/missing."""
        if not self.is_trusted_url(url):
            return None
        if self._use_local:
            path = self._local_path(url)
            if path.exists() and path.is_file():
                return path.read_bytes()
            return None
        try:
            key = self._key_from_url(url)
            if not key:
                return None
            obj = self.s3_client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
            return obj["Body"].read()
        except ClientError as e:
            logger.error(f"S3 read failed: {e}")
            return None

    async def delete_image(self, url: str) -> bool:
        """Delete an image by URL. Supports DPDP Act data deletion requirement."""
        if not self.is_trusted_url(url):
            return False
        if self._use_local:
            try:
                filepath = self._local_path(url)
                if filepath.exists():
                    filepath.unlink()
                return True
            except Exception as e:
                logger.error(f"Local delete failed: {e}")
                return False
        else:
            try:
                key = self._key_from_url(url)
                if not key:
                    return False
                self.s3_client.delete_object(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=key,
                )
                return True
            except ClientError as e:
                logger.error(f"S3 delete failed: {e}")
                return False


# Singleton instance
storage_service = StorageService()
