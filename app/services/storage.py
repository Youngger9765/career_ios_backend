"""Storage service for file uploads to Supabase or local storage"""

import logging
import os
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

# Import settings when available
try:
    from app.core.config import settings

    SUPABASE_URL = getattr(settings, "SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY = getattr(settings, "SUPABASE_SERVICE_KEY", "")
    SUPABASE_BUCKET = getattr(settings, "SUPABASE_BUCKET", "documents")
    STORAGE_TYPE = getattr(settings, "STORAGE_TYPE", "supabase")
except ImportError:
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "documents")
    STORAGE_TYPE = os.getenv("STORAGE_TYPE", "supabase")


class StorageService:
    """Storage service for file uploads using direct HTTP"""

    def __init__(self):
        self.supabase_url = SUPABASE_URL
        self.supabase_key = SUPABASE_SERVICE_KEY
        self.bucket = SUPABASE_BUCKET

        if STORAGE_TYPE == "supabase" and self.supabase_url and self.supabase_key:
            self.enabled = True
            logger.info(f"Storage service initialized for bucket: {self.bucket}")
        else:
            self.enabled = False
            logger.warning("Storage service disabled - missing configuration")

    async def upload_file(
        self, file_content: bytes, file_path: str, content_type: str = "application/pdf"
    ) -> str:
        """
        Upload file to Supabase Storage

        Args:
            file_content: File bytes
            file_path: Path in bucket (e.g., "documents/file.pdf")
            content_type: MIME type

        Returns:
            Public URL or signed URL
        """
        if not self.enabled:
            raise Exception("Supabase client not initialized. Check STORAGE_TYPE and credentials.")

        try:
            # Direct HTTP upload to Supabase Storage API
            url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{file_path}"
            headers = {
                "Authorization": f"Bearer {self.supabase_key}",
                "apikey": self.supabase_key,
                "Content-Type": content_type,
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, content=file_content, headers=headers, timeout=60.0)
                response.raise_for_status()

            # Return public URL
            url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket}/{file_path}"

            return url
        except Exception as e:
            raise Exception(f"Failed to upload file: {str(e)}") from e

    async def download_file(self, file_path: str) -> bytes:
        """Download file from Supabase Storage"""
        if not self.enabled:
            raise Exception("Supabase client not initialized. Check STORAGE_TYPE and credentials.")

        try:
            # Direct HTTP download from Supabase Storage API
            url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{file_path}"
            headers = {
                "Authorization": f"Bearer {self.supabase_key}",
                "apikey": self.supabase_key,
            }

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=60.0)
                response.raise_for_status()
                return response.content
        except Exception as e:
            raise Exception(f"Failed to download file: {str(e)}") from e

    async def delete_file(self, file_path: str) -> bool:
        """Delete file from Supabase Storage"""
        if not self.enabled:
            raise Exception("Supabase client not initialized. Check STORAGE_TYPE and credentials.")

        try:
            # Direct HTTP delete from Supabase Storage API
            url = f"{self.supabase_url}/storage/v1/object/{self.bucket}/{file_path}"
            headers = {
                "Authorization": f"Bearer {self.supabase_key}",
                "apikey": self.supabase_key,
            }

            async with httpx.AsyncClient() as client:
                response = await client.delete(url, headers=headers, timeout=60.0)
                response.raise_for_status()
                return True
        except Exception as e:
            raise Exception(f"Failed to delete file: {str(e)}") from e

    async def create_signed_url(self, file_path: str, expires_in: int = 3600) -> str:
        """
        Create a temporary signed URL for private files

        Args:
            file_path: Path in bucket
            expires_in: URL expiration in seconds (default 1 hour)

        Returns:
            Signed URL
        """
        if not self.enabled:
            raise Exception("Supabase client not initialized. Check STORAGE_TYPE and credentials.")

        try:
            # Direct HTTP request to create signed URL
            url = f"{self.supabase_url}/storage/v1/object/sign/{self.bucket}/{file_path}"
            headers = {
                "Authorization": f"Bearer {self.supabase_key}",
                "apikey": self.supabase_key,
                "Content-Type": "application/json",
            }
            data = {"expiresIn": expires_in}

            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data, timeout=60.0)
                response.raise_for_status()
                result = response.json()
                return result.get("signedURL", "")
        except Exception as e:
            raise Exception(f"Failed to create signed URL: {str(e)}") from e
