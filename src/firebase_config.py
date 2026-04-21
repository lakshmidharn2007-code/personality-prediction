"""Firebase initialization utilities."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import firebase_admin
import streamlit as st
from firebase_admin import credentials, firestore, storage
from streamlit.errors import StreamlitSecretNotFoundError


def _get_secret_value(key: str, default: Any = None) -> Any:
    """Read a configuration value from Streamlit secrets or environment."""
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except StreamlitSecretNotFoundError:
        pass
    return os.getenv(key, default)


def get_firebase_settings() -> Dict[str, Any]:
    """Load Firebase project settings required by the app."""
    firebase_settings = {
        "project_id": _get_secret_value("FIREBASE_PROJECT_ID", "personality-prediction-1bc5c"),
        "storage_bucket": _get_secret_value(
            "FIREBASE_STORAGE_BUCKET",
            "personality-prediction-1bc5c.firebasestorage.app",
        ),
        "web_api_key": _get_secret_value("FIREBASE_WEB_API_KEY", ""),
        "enable_storage_uploads": str(_get_secret_value("ENABLE_STORAGE_UPLOADS", "false")).lower() == "true",
    }
    return firebase_settings


def _load_service_account_info() -> Dict[str, Any]:
    """Load Firebase Admin service account credentials."""
    raw_json = _get_secret_value("FIREBASE_SERVICE_ACCOUNT_JSON")
    if raw_json:
        if isinstance(raw_json, dict):
            return raw_json
        return json.loads(raw_json)

    file_path = _get_secret_value("FIREBASE_SERVICE_ACCOUNT_FILE")
    if file_path and os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    raise RuntimeError(
        "Firebase Admin credentials are missing. Set FIREBASE_SERVICE_ACCOUNT_JSON "
        "or FIREBASE_SERVICE_ACCOUNT_FILE in environment variables or Streamlit secrets."
    )


def initialize_firebase() -> firebase_admin.App:
    """Initialize Firebase Admin SDK once per process."""
    if firebase_admin._apps:
        return firebase_admin.get_app()

    settings = get_firebase_settings()
    service_account_info = _load_service_account_info()
    credential = credentials.Certificate(service_account_info)
    return firebase_admin.initialize_app(
        credential,
        {
            "storageBucket": settings["storage_bucket"],
            "projectId": settings["project_id"],
        },
    )


def get_firestore_client() -> firestore.Client:
    """Return a Firestore client."""
    initialize_firebase()
    return firestore.client()


def get_storage_bucket() -> storage.bucket:
    """Return the Firebase Storage bucket."""
    initialize_firebase()
    return storage.bucket()
