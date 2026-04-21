"""Reusable Streamlit UI blocks."""

from __future__ import annotations

from typing import Dict

import pandas as pd
import streamlit as st


def render_sidebar(is_admin: bool) -> str:
    """Render app navigation."""
    st.sidebar.title("Navigation")
    options = ["Upload & Analyze", "History"]
    if is_admin:
        options.append("Admin Dashboard")
    return st.sidebar.radio("Go to", options=options)


def render_header(title: str, subtitle: str) -> None:
    """Render page heading."""
    st.title(title)
    st.caption(subtitle)


def render_disclaimer() -> None:
    """Render the product disclaimer."""
    st.info(
        "The app can show either a direct model prediction or a rule-based personality tendency, depending on the loaded model. "
        "Any inferred tendency shown from resume text is not a scientific personality diagnosis."
    )


def render_metric_row(record: Dict[str, object]) -> None:
    """Render summary metrics for a record."""
    col1, col2, col3 = st.columns(3)
    prediction_type = record.get("prediction_type", "unknown")
    if prediction_type == "personality":
        col1.metric("Predicted Personality", record.get("personality_tendency", "N/A"))
    else:
        col1.metric("Predicted Category", record.get("predicted_category", "N/A") or "N/A")
    col2.metric("Confidence", f"{float(record.get('confidence', 0)):.2%}")
    if prediction_type == "personality":
        col3.metric("Model Type", "OCEAN / Personality")
    else:
        col3.metric("Tendency", record.get("personality_tendency", "N/A"))


def render_analysis_cards(record: Dict[str, object]) -> None:
    """Render high-level analysis output."""
    left, right = st.columns([2, 1])
    with left:
        st.subheader(record.get("file_name", "Resume"))
        st.write(f"**Candidate:** {record.get('name', 'Not found')}")
        st.write(f"**Email:** {record.get('email', 'Not found')}")
        st.write(f"**Phone:** {record.get('phone', 'Not found')}")
        if record.get("prediction_type") == "personality":
            st.write(f"**Primary Personality Output:** {record.get('primary_prediction', 'Not found')}")
        else:
            st.write(f"**Primary Category Output:** {record.get('primary_prediction', 'Not found')}")
        st.write(f"**Preview:** {record.get('extracted_text_preview', '')}")
        top_scores = record.get("top_scores") or []
        if top_scores:
            st.write(
                "**Top Model Scores:** "
                + ", ".join(f"{item['label']} ({item['score']:.2%})" for item in top_scores[:3])
            )
        personality_profile = record.get("personality_profile") or {}
        if personality_profile:
            st.write("**Big Five Profile:**")
            for trait, details in personality_profile.items():
                st.write(
                    f"{trait}: {details.get('prediction', 'Unknown')} "
                    f"({float(details.get('score', 0)):.2%})"
                )
    with right:
        storage_url = record.get("storage_url", "")
        if storage_url:
            st.link_button("Open Stored File", storage_url, use_container_width=True)
        else:
            st.write("**Stored File:** Not uploaded")
        st.write(f"**Storage Status:** {record.get('storage_status', 'unknown')}")
        st.write(f"**Status:** {record.get('processing_status', 'unknown')}")
        st.write(f"**Uploaded At:** {record.get('uploaded_at', '-')}")


def render_parsed_fields(parsed_fields: Dict[str, object]) -> None:
    """Render parsed resume fields."""
    st.write("**Parsed Fields**")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Summary:** {parsed_fields.get('summary', 'Not found')}")
        st.write(f"**Education:** {parsed_fields.get('education', 'Not found')}")
    with col2:
        st.write(f"**Experience:** {parsed_fields.get('experience', 'Not found')}")
        skills = parsed_fields.get("skills", [])
        st.write("**Skills:** " + (", ".join(skills) if skills else "Not found"))


def render_history_table(dataframe: pd.DataFrame) -> None:
    """Render saved analyses in a table."""
    display_columns = [
        column
        for column in [
            "upload_id",
            "file_name",
            "name",
            "email",
            "prediction_type",
            "primary_prediction",
            "predicted_category",
            "confidence",
            "personality_tendency",
            "skills",
            "created_at",
        ]
        if column in dataframe.columns
    ]
    st.dataframe(dataframe[display_columns], use_container_width=True, hide_index=True)
