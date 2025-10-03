"""Storage service for file uploads to Supabase or local storage"""

import os
from typing import Optional

try:
    from supabase import Client, create_client

    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

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
    """Storage service for file uploads"""

    def __init__(self):
        if STORAGE_TYPE == "supabase" and SUPABASE_AVAILABLE and SUPABASE_URL and SUPABASE_SERVICE_KEY:
            try:
                self.supabase: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
                self.bucket = SUPABASE_BUCKET
            except Exception as e:
                print(f"Warning: Failed to initialize Supabase client: {e}")
                self.supabase = None
                self.bucket = SUPABASE_BUCKET
        else:
            self.supabase = None
            self.bucket = SUPABASE_BUCKET

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
        if not self.supabase:
            raise Exception("Supabase client not initialized. Check STORAGE_TYPE and credentials.")

        try:
            # Upload to Supabase Storage
            self.supabase.storage.from_(self.bucket).upload(
                path=file_path,
                file=file_content,
                file_options={"content-type": content_type},
            )

            # Get public URL (bucket must be public) or create signed URL
            url = self.supabase.storage.from_(self.bucket).get_public_url(file_path)

            return url
        except Exception as e:
            raise Exception(f"Failed to upload file: {str(e)}") from e

    async def download_file(self, file_path: str) -> bytes:
        """Download file from Supabase Storage"""
        if not self.supabase:
            raise Exception("Supabase client not initialized")

        try:
            response = self.supabase.storage.from_(self.bucket).download(file_path)
            return response
        except Exception as e:
            raise Exception(f"Failed to download file: {str(e)}") from e

    async def delete_file(self, file_path: str) -> bool:
        """Delete file from Supabase Storage"""
        if not self.supabase:
            raise Exception("Supabase client not initialized")

        try:
            self.supabase.storage.from_(self.bucket).remove([file_path])
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
        if not self.supabase:
            raise Exception("Supabase client not initialized")

        try:
            response = self.supabase.storage.from_(self.bucket).create_signed_url(
                path=file_path, expires_in=expires_in
            )
            return response["signedURL"]
        except Exception as e:
            raise Exception(f"Failed to create signed URL: {str(e)}") from e


# Singleton instance
storage_service = StorageService()
