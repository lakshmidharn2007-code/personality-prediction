"""Authentication service using Firebase Auth REST API and Firestore."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

import requests

from src.firebase_config import get_firebase_settings
from src.firestore_service import FirestoreService
from src.utils import now_iso


PRIMARY_ADMIN_EMAIL = "lakshmidhar2007@gmail.com"


@dataclass
class AuthUser:
    """Authenticated user view model."""

    user_id: str
    email: str
    full_name: str
    is_admin: bool = False

    def to_dict(self) -> Dict[str, str]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "full_name": self.full_name,
            "is_admin": self.is_admin,
        }


class AuthService:
    """Simple authentication layer backed by Firebase Auth."""

    def __init__(self) -> None:
        settings = get_firebase_settings()
        self.api_key = settings["web_api_key"]
        self.firestore_service = FirestoreService()

    def _require_api_key(self) -> None:
        if not self.api_key:
            raise RuntimeError(
                "FIREBASE_WEB_API_KEY is not configured. Add it to environment variables or Streamlit secrets."
            )

    def register(self, email: str, password: str, full_name: str, request_admin: bool = False) -> Dict[str, str]:
        """Create a Firebase Auth user and a matching Firestore user profile."""
        self._require_api_key()
        endpoint = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={self.api_key}"
        response = requests.post(
            endpoint,
            json={
                "email": email,
                "password": password,
                "returnSecureToken": True,
            },
            timeout=30,
        )
        payload = response.json()
        if response.status_code >= 400:
            message = payload.get("error", {}).get("message", "Registration failed.")
            raise RuntimeError(message)

        is_primary_admin = email.strip().lower() == PRIMARY_ADMIN_EMAIL
        user = AuthUser(
            user_id=payload["localId"],
            email=email,
            full_name=full_name or email.split("@")[0],
            is_admin=is_primary_admin,
        )
        self.firestore_service.upsert_user_profile(
            {
                "user_id": user.user_id,
                "email": user.email,
                "full_name": user.full_name,
                "is_admin": user.is_admin,
                "approved_admin": user.is_admin,
                "created_at": now_iso(),
            }
        )
        if request_admin and not is_primary_admin:
            self.firestore_service.create_admin_request(
                {
                    "user_id": user.user_id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "status": "pending",
                    "requested_at": now_iso(),
                }
            )
        return user.to_dict()

    def login(self, email: str, password: str) -> Dict[str, str]:
        """Authenticate an existing Firebase Auth user."""
        self._require_api_key()
        endpoint = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.api_key}"
        response = requests.post(
            endpoint,
            json={
                "email": email,
                "password": password,
                "returnSecureToken": True,
            },
            timeout=30,
        )
        payload = response.json()
        if response.status_code >= 400:
            message = payload.get("error", {}).get("message", "Login failed.")
            raise RuntimeError(message)

        profile = self.firestore_service.get_user_profile(payload["localId"]) or {}
        is_primary_admin = email.strip().lower() == PRIMARY_ADMIN_EMAIL
        if is_primary_admin and not profile.get("is_admin", False):
            self.firestore_service.upsert_user_profile(
                {
                    "user_id": payload["localId"],
                    "email": email,
                    "full_name": profile.get("full_name", email.split("@")[0]),
                    "is_admin": True,
                    "approved_admin": True,
                    "updated_at": now_iso(),
                }
            )
        user = AuthUser(
            user_id=payload["localId"],
            email=email,
            full_name=profile.get("full_name", email.split("@")[0]),
            is_admin=is_primary_admin or bool(profile.get("approved_admin", False)),
        )
        return user.to_dict()
