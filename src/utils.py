"""General utility helpers."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Iterable, List

import pandas as pd
import streamlit as st
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize


def ensure_session_state() -> None:
    """Initialize required Streamlit session state keys."""
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("latest_results", [])


def generate_upload_id() -> str:
    """Return a unique upload ID."""
    return str(uuid.uuid4())


def now_iso() -> str:
    """Return the current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def clean_text(text: str) -> str:
    """Normalize raw resume text for simple NLP steps."""
    normalized = re.sub(r"[^A-Za-z0-9@.+#/\-\s]", " ", text or "")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    try:
        tokens = word_tokenize(normalized.lower())
        stop_words = set(stopwords.words("english"))
        filtered = [token for token in tokens if token not in stop_words]
        return " ".join(filtered)
    except LookupError:
        return normalized.lower()


def shorten_text(text: str, limit: int = 300) -> str:
    """Shorten a block of text for previews."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def flatten_skills(skills: object) -> str:
    """Convert skills to a CSV-friendly string."""
    if isinstance(skills, list):
        return ", ".join(str(item) for item in skills)
    return str(skills or "")


def record_to_dataframe(records: Iterable[dict]) -> pd.DataFrame:
    """Convert analysis records into a DataFrame."""
    rows: List[dict] = []
    for record in records:
        parsed_fields = record.get("parsed_fields", {})
        rows.append(
            {
                "upload_id": record.get("upload_id"),
                "file_name": record.get("file_name"),
                "name": record.get("name") or parsed_fields.get("name"),
                "email": record.get("email") or parsed_fields.get("email"),
                "phone": record.get("phone") or parsed_fields.get("phone"),
                "predicted_category": record.get("predicted_category"),
                "prediction_type": record.get("prediction_type"),
                "primary_prediction": record.get("primary_prediction"),
                "confidence": record.get("confidence"),
                "personality_tendency": record.get("personality_tendency"),
                "skills": flatten_skills(record.get("skills") or parsed_fields.get("skills", [])),
                "education": record.get("education") or parsed_fields.get("education"),
                "experience": record.get("experience") or parsed_fields.get("experience"),
                "summary": record.get("summary") or parsed_fields.get("summary"),
                "top_scores": str(record.get("top_scores", "")),
                "personality_profile": str(record.get("personality_profile", "")),
                "created_at": record.get("created_at"),
                "storage_url": record.get("storage_url"),
                "storage_status": record.get("storage_status"),
                "status": record.get("status"),
            }
        )
    return pd.DataFrame(rows)


def dataframe_to_csv_bytes(dataframe: pd.DataFrame) -> bytes:
    """Serialize a DataFrame as CSV bytes."""
    return dataframe.to_csv(index=False).encode("utf-8")
