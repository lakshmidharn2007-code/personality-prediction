"""Firebase Storage upload helpers."""

from __future__ import annotations

from src.firebase_config import get_firebase_settings, get_storage_bucket


class StorageUnavailableError(RuntimeError):
    """Raised when Firebase Storage is disabled or unavailable."""


class StorageService:
    """Upload resume files to Firebase Storage."""

    def __init__(self) -> None:
        settings = get_firebase_settings()
        self.enabled = settings["enable_storage_uploads"]
        self.bucket = get_storage_bucket() if self.enabled else None

    def upload_resume(self, user_id: str, upload_id: str, uploaded_file) -> str:
        """Upload a resume to the configured storage bucket."""
        if not self.enabled or self.bucket is None:
            raise StorageUnavailableError(
                "Firebase Storage uploads are disabled. Set ENABLE_STORAGE_UPLOADS=true after enabling Storage in Firebase."
            )
        blob_path = f"resumes/{user_id}/{upload_id}/{uploaded_file.name}"
        blob = self.bucket.blob(blob_path)
        blob.upload_from_string(
            uploaded_file.getvalue(),
            content_type=uploaded_file.type or "application/octet-stream",
        )
        blob.make_public()
        return blob.public_url
