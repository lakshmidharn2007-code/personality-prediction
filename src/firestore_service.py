"""Firestore persistence service."""

from __future__ import annotations

from typing import Dict, List, Optional

from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from src.firebase_config import get_firestore_client


class FirestoreService:
    """Read and write app data in Firestore."""

    def __init__(self) -> None:
        self.db = get_firestore_client()

    def upsert_user_profile(self, profile: Dict[str, object]) -> None:
        """Create or update a user profile."""
        self.db.collection("users").document(str(profile["user_id"])).set(profile, merge=True)

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, object]]:
        """Fetch a user profile."""
        snapshot = self.db.collection("users").document(user_id).get()
        return snapshot.to_dict() if snapshot.exists else None

    def create_admin_request(self, request: Dict[str, object]) -> None:
        """Create or update an admin access request."""
        self.db.collection("admin_requests").document(str(request["user_id"])).set(request, merge=True)

    def get_pending_admin_requests(self) -> List[Dict[str, object]]:
        """Return pending admin access requests."""
        query = self.db.collection("admin_requests").where(filter=FieldFilter("status", "==", "pending"))
        return [document.to_dict() for document in query.stream()]

    def approve_admin_request(self, user_id: str, approved_by: str) -> None:
        """Approve a pending admin request and grant admin access."""
        self.db.collection("users").document(user_id).set(
            {
                "is_admin": True,
                "approved_admin": True,
            },
            merge=True,
        )
        self.db.collection("admin_requests").document(user_id).set(
            {
                "status": "approved",
                "approved_by": approved_by,
                "approved_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )

    def reject_admin_request(self, user_id: str, rejected_by: str) -> None:
        """Reject a pending admin request."""
        self.db.collection("admin_requests").document(user_id).set(
            {
                "status": "rejected",
                "rejected_by": rejected_by,
                "rejected_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True,
        )

    def create_analysis_record(self, record: Dict[str, object]) -> None:
        """Persist analysis output in two collections for simple querying."""
        upload_id = str(record["upload_id"])
        self.db.collection("resume_uploads").document(upload_id).set(record)
        self.db.collection("analysis_results").document(upload_id).set(record)

    def get_analysis_records_for_user(self, user_id: str) -> List[Dict[str, object]]:
        """Return all analysis results for a single user."""
        query = (
            self.db.collection("analysis_results")
            .where(filter=FieldFilter("user_id", "==", user_id))
            .order_by("created_at", direction=firestore.Query.DESCENDING)
        )
        return [document.to_dict() for document in query.stream()]

    def get_all_analysis_records(self) -> List[Dict[str, object]]:
        """Return all analysis results across users."""
        query = self.db.collection("analysis_results").order_by(
            "created_at",
            direction=firestore.Query.DESCENDING,
        )
        return [document.to_dict() for document in query.stream()]
