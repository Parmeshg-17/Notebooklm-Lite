"""
Object Storage service — S3-compatible via boto3 with local filesystem fallback.
Supports MinIO/AWS S3 for production and local disk storage for seamless local dev.
"""

import io
import os
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class StorageService:
    """Object storage service supporting both S3-compatible endpoints and local disk."""

    def __init__(self) -> None:
        self._bucket = settings.s3_bucket
        self._use_local = (settings.storage_provider == "local")
        self._local_dir = Path("data/storage") / self._bucket
        self._local_dir.mkdir(parents=True, exist_ok=True)
        self._client = None

        if not self._use_local:
            try:
                self._client = boto3.client(
                    "s3",
                    endpoint_url=settings.s3_endpoint,
                    aws_access_key_id=settings.s3_access_key,
                    aws_secret_access_key=settings.s3_secret_key,
                    config=Config(
                        signature_version="s3v4",
                        connect_timeout=2,
                        read_timeout=2,
                        retries={"max_attempts": 1},
                    ),
                    use_ssl=settings.s3_use_ssl,
                )
                self._client.list_buckets()
                logger.info("StorageService connected to S3/MinIO endpoint", endpoint=settings.s3_endpoint)
            except Exception as e:
                logger.info("S3 endpoint unavailable, using local disk storage fallback", path=str(self._local_dir), reason=str(e))
                self._use_local = True
                self._client = None
        else:
            logger.info("StorageService initialized with local disk storage", path=str(self._local_dir))
            self._client = None

    def health_check(self) -> bool:
        """Check if storage service is healthy."""
        if self._use_local:
            return self._local_dir.exists() and os.access(self._local_dir, os.W_OK)
        try:
            self._client.list_buckets()
            return True
        except Exception:
            return self._local_dir.exists()

    def ensure_bucket(self) -> None:
        """Create bucket or directory if it doesn't exist."""
        if self._use_local:
            self._local_dir.mkdir(parents=True, exist_ok=True)
            return

        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            try:
                self._client.create_bucket(Bucket=self._bucket)
                logger.info("Created S3 bucket", bucket=self._bucket)
            except Exception as e:
                logger.warning("Could not create S3 bucket, switching to local storage", error=str(e))
                self._use_local = True
                self._local_dir.mkdir(parents=True, exist_ok=True)

    def upload_file(
        self,
        file_obj: BinaryIO,
        storage_key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload file-like object and return the storage key."""
        if self._use_local:
            target_path = self._local_dir / storage_key
            target_path.parent.mkdir(parents=True, exist_ok=True)
            file_obj.seek(0)
            with open(target_path, "wb") as f:
                f.write(file_obj.read())
            logger.info("Uploaded file to local storage", key=storage_key, path=str(target_path))
            return storage_key

        try:
            file_obj.seek(0)
            self._client.upload_fileobj(
                file_obj,
                self._bucket,
                storage_key,
                ExtraArgs={"ContentType": content_type},
            )
            logger.info("Uploaded file to S3", key=storage_key, bucket=self._bucket)
            return storage_key
        except Exception as e:
            logger.warning("S3 upload failed, saving to local storage fallback", error=str(e))
            target_path = self._local_dir / storage_key
            target_path.parent.mkdir(parents=True, exist_ok=True)
            file_obj.seek(0)
            with open(target_path, "wb") as f:
                f.write(file_obj.read())
            return storage_key

    def download_file(self, storage_key: str) -> bytes:
        """Download file and return as bytes."""
        local_path = self._local_dir / storage_key
        if local_path.exists():
            with open(local_path, "rb") as f:
                return f.read()

        if self._client:
            try:
                buf = io.BytesIO()
                self._client.download_fileobj(self._bucket, storage_key, buf)
                buf.seek(0)
                return buf.read()
            except Exception as e:
                logger.error("Failed to download from S3", key=storage_key, error=str(e))

        raise FileNotFoundError(f"File {storage_key} not found in storage")

    def delete_file(self, storage_key: str) -> None:
        """Delete object from storage."""
        local_path = self._local_dir / storage_key
        if local_path.exists():
            try:
                local_path.unlink()
                logger.info("Deleted local file", key=storage_key)
            except Exception as e:
                logger.error("Failed to delete local file", key=storage_key, error=str(e))

        if self._client:
            try:
                self._client.delete_object(Bucket=self._bucket, Key=storage_key)
                logger.info("Deleted S3 file", key=storage_key)
            except Exception as e:
                logger.warning("Failed to delete S3 file", key=storage_key, error=str(e))

    def generate_presigned_url(self, storage_key: str, expires_in: int = 3600) -> str:
        """Generate a temporary URL for direct download."""
        if self._use_local or not self._client:
            return f"/api/v1/documents/raw/{storage_key}"

        try:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": storage_key},
                ExpiresIn=expires_in,
            )
        except Exception:
            return f"/api/v1/documents/raw/{storage_key}"


_storage_service: StorageService | None = None


def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
