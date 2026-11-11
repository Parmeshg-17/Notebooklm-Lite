"""
Production Storage Service supporting Local Filesystem and Amazon S3.
Implements:
- Path traversal defense & filename sanitization
- Magic-byte PDF signature validation (%PDF-)
- Server-side encrypted S3 uploads (AES256)
- Presigned upload & download URL generation with strict TTL
- Safe S3 object streaming to temporary files for processing
- Multi-tenant path isolation by user ID
"""

import logging
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import BadRequestException

logger = logging.getLogger("app.services.storage_service")

# Lazy-loaded boto3 client
_s3_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is not None:
        return _s3_client

    try:
        import boto3
        from botocore.config import Config

        client_kwargs: Dict[str, Any] = {
            "region_name": settings.AWS_REGION,
            "config": Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        }
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            client_kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            client_kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        if settings.S3_ENDPOINT_URL:
            client_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL

        _s3_client = boto3.client("s3", **client_kwargs)
        return _s3_client
    except Exception as e:
        logger.warning(f"Failed to initialize boto3 S3 client: {e}")
        return None


class StorageService:
    @staticmethod
    def is_s3_enabled() -> bool:
        """Check if S3 storage backend is configured and active."""
        return settings.STORAGE_BACKEND.lower() == "s3" and bool(settings.S3_BUCKET_NAME)

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent directory traversal and illegal characters."""
        base = os.path.basename(filename)
        cleaned = re.sub(r"[^\w\s\.-]", "", base).strip()
        cleaned = re.sub(r"\.{2,}", ".", cleaned)  # Remove multiple dots
        return cleaned or "document.pdf"

    @staticmethod
    def validate_pdf_bytes(header_bytes: bytes) -> bool:
        """Verify magic byte header signature for PDF (%PDF-)."""
        return header_bytes.startswith(b"%PDF-")

    @classmethod
    async def save_upload_file(cls, file: UploadFile, user_id: uuid.UUID) -> Tuple[str, str, int]:
        """
        Save uploaded file to local filesystem or S3 based on configured backend.
        Returns: (safe_filename, storage_path_or_key, file_size)
        """
        safe_name = cls.sanitize_filename(file.filename or "upload.pdf")
        unique_id = uuid.uuid4().hex[:12]
        stored_filename = f"{unique_id}_{safe_name}"

        # 1. Read initial chunk to validate magic bytes
        first_chunk = await file.read(1024)
        if not first_chunk:
            raise BadRequestException("Uploaded file is empty.")

        # Check PDF header if claimed to be PDF
        if safe_name.lower().endswith(".pdf") and not cls.validate_pdf_bytes(first_chunk):
            raise BadRequestException("Invalid PDF file: Missing %PDF- header signature.")

        # 2. If S3 is enabled, upload directly to private S3 bucket
        if cls.is_s3_enabled():
            s3 = get_s3_client()
            if s3:
                s3_key = f"uploads/{user_id}/{stored_filename}"
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(safe_name).suffix) as tmp:
                    tmp.write(first_chunk)
                    total_size = len(first_chunk)
                    chunk_size = 1024 * 1024
                    while chunk := await file.read(chunk_size):
                        total_size += len(chunk)
                        if total_size > settings.MAX_UPLOAD_SIZE_BYTES:
                            tmp.close()
                            os.unlink(tmp.name)
                            raise BadRequestException(
                                f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB"
                            )
                        tmp.write(chunk)
                    tmp_path = tmp.name

                try:
                    s3.upload_file(
                        tmp_path,
                        settings.S3_BUCKET_NAME,
                        s3_key,
                        ExtraArgs={
                            "ServerSideEncryption": "AES256",
                            "ContentType": file.content_type or "application/pdf",
                            "Metadata": {
                                "original_filename": safe_name,
                                "owner_id": str(user_id),
                            },
                        },
                    )
                    logger.info(f"[S3] Uploaded {safe_name} to s3://{settings.S3_BUCKET_NAME}/{s3_key}")
                    return safe_name, f"s3://{settings.S3_BUCKET_NAME}/{s3_key}", total_size
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)

        # 3. Local filesystem storage fallback
        user_upload_dir = settings.upload_path / str(user_id)
        user_upload_dir.mkdir(parents=True, exist_ok=True)
        dest_path = user_upload_dir / stored_filename

        total_size = len(first_chunk)
        chunk_size = 1024 * 1024

        with open(dest_path, "wb") as f:
            f.write(first_chunk)
            while chunk := await file.read(chunk_size):
                total_size += len(chunk)
                if total_size > settings.MAX_UPLOAD_SIZE_BYTES:
                    f.close()
                    if dest_path.exists():
                        dest_path.unlink()
                    raise BadRequestException(
                        f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)}MB"
                    )
                f.write(chunk)

        return safe_name, str(dest_path.resolve()), total_size

    @classmethod
    def generate_presigned_upload_url(
        cls,
        user_id: uuid.UUID,
        filename: str,
        content_type: str = "application/pdf",
        expires_in: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate presigned S3 PUT URL for direct client upload."""
        if not cls.is_s3_enabled():
            raise BadRequestException("S3 storage is not enabled in this environment.")

        s3 = get_s3_client()
        if not s3:
            raise BadRequestException("S3 client is unavailable.")

        safe_name = cls.sanitize_filename(filename)
        unique_id = uuid.uuid4().hex[:12]
        s3_key = f"uploads/{user_id}/{unique_id}_{safe_name}"
        ttl = expires_in or settings.PRESIGNED_URL_EXPIRE_SECONDS

        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.S3_BUCKET_NAME,
                "Key": s3_key,
                "ContentType": content_type,
                "ServerSideEncryption": "AES256",
            },
            ExpiresIn=ttl,
        )

        return {
            "upload_url": url,
            "s3_key": s3_key,
            "storage_path": f"s3://{settings.S3_BUCKET_NAME}/{s3_key}",
            "expires_in_seconds": ttl,
            "filename": safe_name,
        }

    @classmethod
    def generate_presigned_download_url(
        cls,
        storage_path: str,
        filename: Optional[str] = None,
        expires_in: Optional[int] = None,
    ) -> Optional[str]:
        """Generate presigned S3 GET URL for viewing or downloading the document."""
        if not storage_path.startswith("s3://"):
            return None

        s3 = get_s3_client()
        if not s3:
            return None

        # Parse bucket and key from s3://bucket/key
        parts = storage_path.replace("s3://", "").split("/", 1)
        if len(parts) != 2:
            return None
        bucket, key = parts[0], parts[1]
        ttl = expires_in or settings.PRESIGNED_URL_EXPIRE_SECONDS

        params: Dict[str, Any] = {
            "Bucket": bucket,
            "Key": key,
            "ResponseContentType": "application/pdf",
        }
        if filename:
            params["ResponseContentDisposition"] = f'inline; filename="{cls.sanitize_filename(filename)}"'

        return s3.generate_presigned_url(
            ClientMethod="get_object",
            Params=params,
            ExpiresIn=ttl,
        )

    @classmethod
    def resolve_to_local_path(cls, storage_path: str) -> Tuple[str, bool]:
        """
        Ensures the document is accessible locally for PyMuPDF extraction.
        If stored in S3, downloads to a managed temporary file.
        Returns: (local_file_path, is_temporary)
        """
        if not storage_path.startswith("s3://"):
            return storage_path, False

        s3 = get_s3_client()
        if not s3:
            raise FileNotFoundError(f"S3 client unavailable to fetch {storage_path}")

        parts = storage_path.replace("s3://", "").split("/", 1)
        bucket, key = parts[0], parts[1]

        suffix = Path(key).suffix or ".pdf"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.close()

        logger.info(f"[S3] Downloading {storage_path} to temporary file {tmp.name}")
        s3.download_file(bucket, key, tmp.name)
        return tmp.name, True

    @staticmethod
    def delete_file(storage_path: str) -> bool:
        """Safely delete file from local storage or S3 bucket."""
        try:
            if storage_path.startswith("s3://"):
                s3 = get_s3_client()
                if s3:
                    parts = storage_path.replace("s3://", "").split("/", 1)
                    if len(parts) == 2:
                        s3.delete_object(Bucket=parts[0], Key=parts[1])
                        logger.info(f"[S3] Deleted {storage_path}")
                        return True
            else:
                p = Path(storage_path)
                if p.exists() and p.is_file():
                    p.unlink()
                    return True
        except Exception as e:
            logger.warning(f"Failed to delete file at {storage_path}: {e}")
        return False
