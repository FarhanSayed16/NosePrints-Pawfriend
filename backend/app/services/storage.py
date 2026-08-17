"""
S3-compatible object storage service.
Handles photo uploads to Cloudflare R2 / Backblaze B2 / AWS S3.
Falls back to local filesystem storage for development.
"""

import uuid
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from app.config import settings
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
                logger.info(f"S3 storage initialized: {settings.S3_ENDPOINT_URL}")
            except Exception as e:
                logger.warning(f"S3 init failed, falling back to local: {e}")
                self._use_local = True
        else:
            logger.info("S3 not configured — using local filesystem storage")
            self._use_local = True

        if self._use_local:
            self._local_dir.mkdir(parents=True, exist_ok=True)

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
            url = f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}/{key}"
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

    async def delete_image(self, url: str) -> bool:
        """Delete an image by URL. Supports DPDP Act data deletion requirement."""
        if self._use_local:
            try:
                filepath = Path(url.lstrip("/"))
                if filepath.exists():
                    filepath.unlink()
                return True
            except Exception as e:
                logger.error(f"Local delete failed: {e}")
                return False
        else:
            try:
                key = url.split(f"{settings.S3_BUCKET_NAME}/")[-1]
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
