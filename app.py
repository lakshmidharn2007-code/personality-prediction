"""Streamlit entrypoint for the AI Resume Personality Analyzer MVP."""

from __future__ import annotations

from io import BytesIO
from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

from src.auth_service import AuthService
from src.firestore_service import FirestoreService
from src.parser import ResumeParser
from src.predictor import ResumePredictor
from src.storage_service import StorageService, StorageUnavailableError
from src.ui_components import (
    render_analysis_cards,
    render_disclaimer,
    render_header,
    render_history_table,
    render_metric_row,
    render_parsed_fields,
    render_sidebar,
)
from src.utils import (
    dataframe_to_csv_bytes,
    ensure_session_state,
    generate_upload_id,
    now_iso,
    record_to_dataframe,
    shorten_text,
)


st.set_page_config(
    page_title="AI Resume Personality Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

ensure_session_state()


@st.cache_resource(show_spinner=False)
def get_services() -> Dict[str, object]:
    """Create long-lived application services."""
    return {
        "auth_service": AuthService(),
        "storage_service": StorageService(),
        "firestore_service": FirestoreService(),
        "parser": ResumeParser(),
        "predictor": ResumePredictor(),
    }


def handle_login(auth_service: AuthService) -> Optional[dict]:
    """Render login/register form and return the authenticated user."""
    st.subheader("Sign in")
    auth_tab, register_tab = st.tabs(["Login", "Register"])

    user = None

    with auth_tab:
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login", use_container_width=True)
        if submitted:
            try:
                user = auth_service.login(email=email, password=password)
                st.session_state["user"] = user
                st.success("Logged in successfully.")
                st.rerun()
            except Exception as exc:  # pragma: no cover - streamlit feedback path
                st.error(str(exc))

    with register_tab:
        with st.form("register_form", clear_on_submit=False):
            full_name = st.text_input("Full name", key="register_name")
            email = st.text_input("Email", key="register_email")
            password = st.text_input("Password", type="password", key="register_password")
            request_admin = st.checkbox("Request admin access", value=False)
            submitted = st.form_submit_button("Register", use_container_width=True)
        if submitted:
            try:
                user = auth_service.register(
                    email=email,
                    password=password,
                    full_name=full_name,
                    request_admin=request_admin,
                )
                st.session_state["user"] = user
                st.success("Account created successfully.")
                if request_admin and not user.get("is_admin"):
                    st.info("Admin access request sent. Access is granted only after approval.")
                st.rerun()
            except Exception as exc:  # pragma: no cover - streamlit feedback path
                st.error(str(exc))

    return user


def process_uploaded_files(
    files: List[BytesIO],
    parser: ResumeParser,
    predictor: ResumePredictor,
    storage_service: StorageService,
    firestore_service: FirestoreService,
    user: dict,
) -> List[dict]:
    """Process uploaded resumes and persist results."""
    processed_records: List[dict] = []

    for uploaded_file in files:
        upload_id = generate_upload_id()
        with st.status(f"Processing `{uploaded_file.name}`", expanded=False) as status:
            status.write("Extracting resume text")
            raw_text = parser.extract_text_from_upload(uploaded_file)
            status.write("Parsing candidate details")
            parsed_fields = parser.parse_resume(raw_text)
            status.write("Running model prediction")
            prediction = predictor.predict(raw_text)
            prediction_type = prediction["prediction_type"]
            predicted_category = ""
            personality = ""

            if prediction_type == "personality":
                personality = prediction["primary_label"]
            else:
                predicted_category = prediction["primary_label"]
                personality = predictor.infer_personality_tendency(
                    skills=parsed_fields.get("skills", []),
                    experience=parsed_fields.get("experience", ""),
                    summary=parsed_fields.get("summary", ""),
                )

            storage_url = ""
            storage_status = "skipped"
            status.write("Handling file storage")
            try:
                storage_url = storage_service.upload_resume(
                    user_id=user["user_id"],
                    upload_id=upload_id,
                    uploaded_file=uploaded_file,
                )
                storage_status = "uploaded"
            except StorageUnavailableError:
                status.write("Firebase Storage is disabled for free-plan mode. Continuing without cloud file upload.")
            except Exception as exc:
                storage_status = "failed"
                status.write(f"Cloud file upload failed: {exc}. Continuing with metadata-only save.")

            record = {
                "upload_id": upload_id,
                "user_id": user["user_id"],
                "user_email": user["email"],
                "file_name": uploaded_file.name,
                "storage_url": storage_url,
                "storage_status": storage_status,
                "uploaded_at": now_iso(),
                "extracted_text_preview": shorten_text(raw_text, limit=500),
                "parsed_fields": parsed_fields,
                "prediction_type": prediction_type,
                "predicted_category": predicted_category,
                "confidence": prediction["confidence"],
                "personality_tendency": personality,
                "primary_prediction": prediction["primary_label"],
                "top_scores": prediction["top_scores"],
                "model_labels": prediction["model_labels"],
                "personality_profile": prediction.get("personality_profile", {}),
                "processing_status": "completed",
                "status": "completed",
                "email": parsed_fields.get("email"),
                "phone": parsed_fields.get("phone"),
                "skills": parsed_fields.get("skills", []),
                "education": parsed_fields.get("education", ""),
                "experience": parsed_fields.get("experience", ""),
                "summary": parsed_fields.get("summary", ""),
                "name": parsed_fields.get("name"),
                "created_at": now_iso(),
            }

            status.write("Saving analysis to Firestore")
            firestore_service.create_analysis_record(record)
            processed_records.append(record)
            status.update(label=f"Completed `{uploaded_file.name}`", state="complete")

    return processed_records


def render_upload_page(
    parser: ResumeParser,
    predictor: ResumePredictor,
    storage_service: StorageService,
    firestore_service: FirestoreService,
    user: dict,
) -> None:
    """Render the main upload workflow."""
    render_header(
        "AI Resume Personality Analyzer",
        "Upload PDF or DOCX resumes, parse core profile details, run the trained model, and save structured history to Firebase.",
    )

    uploads = st.file_uploader(
        "Upload one or more resumes",
        type=["pdf", "docx"],
        accept_multiple_files=True,
        help="Supported file types: PDF and DOCX",
    )

    if uploads:
        st.caption("Uploaded files")
        for file in uploads:
            st.write(f"- `{file.name}`")

    analyze = st.button("Analyze Resumes", type="primary", use_container_width=True)
    if analyze and uploads:
        records = process_uploaded_files(
            files=uploads,
            parser=parser,
            predictor=predictor,
            storage_service=storage_service,
            firestore_service=firestore_service,
            user=user,
        )
        st.session_state["latest_results"] = records
        st.success(f"Processed {len(records)} resume(s).")
    elif analyze and not uploads:
        st.warning("Upload at least one PDF or DOCX file before starting analysis.")

    latest_results = st.session_state.get("latest_results", [])
    if latest_results:
        st.divider()
        st.subheader("Latest Analysis Results")
        for result in latest_results:
            render_metric_row(result)
            render_analysis_cards(result)
            render_parsed_fields(result["parsed_fields"])
            st.markdown("---")

        export_df = record_to_dataframe(latest_results)
        st.download_button(
            "Download latest results as CSV",
            data=dataframe_to_csv_bytes(export_df),
            file_name="latest_resume_analysis.csv",
            mime="text/csv",
            use_container_width=True,
        )


def render_history_page(firestore_service: FirestoreService, user: dict) -> None:
    """Render analysis history for the current user."""
    render_header(
        "Analysis History",
        "Review previous uploads stored in Firestore and export filtered results.",
    )
    records = firestore_service.get_analysis_records_for_user(user["user_id"])
    history_df = record_to_dataframe(records)

    if history_df.empty:
        st.info("No saved analyses found for this account yet.")
        return

    search = st.text_input("Search history", placeholder="Search by file name, email, skills, or category")
    category_filter = st.selectbox(
        "Filter by predicted category",
        options=["All"] + sorted(history_df["predicted_category"].dropna().unique().tolist()),
    )
    tendency_filter = st.selectbox(
        "Filter by personality tendency",
        options=["All"] + sorted(history_df["personality_tendency"].dropna().unique().tolist()),
    )

    filtered_df = history_df.copy()
    if search:
        search_lower = search.lower()
        mask = filtered_df.apply(
            lambda row: any(search_lower in str(value).lower() for value in row.values),
            axis=1,
        )
        filtered_df = filtered_df[mask]
    if category_filter != "All":
        filtered_df = filtered_df[filtered_df["predicted_category"] == category_filter]
    if tendency_filter != "All":
        filtered_df = filtered_df[filtered_df["personality_tendency"] == tendency_filter]

    render_history_table(filtered_df)
    st.download_button(
        "Download history as CSV",
        data=dataframe_to_csv_bytes(filtered_df),
        file_name="resume_analysis_history.csv",
        mime="text/csv",
        use_container_width=True,
    )


def render_admin_page(firestore_service: FirestoreService, user: dict) -> None:
    """Render recruiter/admin view across all analyses."""
    render_header(
        "Recruiter Dashboard",
        "Browse all resume analyses across the project with filters useful for demos or recruiter review.",
    )

    if not user.get("is_admin"):
        st.warning("Admin access is required to view all uploaded analyses.")
        return

    render_disclaimer()
    st.warning(
        "Free-plan mode is active: original resume files are not uploaded to Firebase Storage. "
        "Analysis results and history are still saved in Firestore."
    )

    st.subheader("Admin Access Requests")
    pending_requests = firestore_service.get_pending_admin_requests()
    if pending_requests:
        for request in pending_requests:
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.write(
                f"**{request.get('full_name', 'Unknown')}** | "
                f"{request.get('email', 'No email')} | "
                f"Requested: {request.get('requested_at', '-')}"
            )
            if col2.button("Approve", key=f"approve_{request['user_id']}", use_container_width=True):
                firestore_service.approve_admin_request(request["user_id"], user["user_id"])
                st.success("Admin request approved.")
                st.rerun()
            if col3.button("Reject", key=f"reject_{request['user_id']}", use_container_width=True):
                firestore_service.reject_admin_request(request["user_id"], user["user_id"])
                st.success("Admin request rejected.")
                st.rerun()
    else:
        st.info("No pending admin access requests.")

    records = firestore_service.get_all_analysis_records()
    admin_df = record_to_dataframe(records)
    if admin_df.empty:
        st.info("No analysis records are available yet.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        category_filter = st.selectbox(
            "Category",
            options=["All"] + sorted(admin_df["predicted_category"].dropna().unique().tolist()),
            key="admin_category_filter",
        )
    with col2:
        tendency_filter = st.selectbox(
            "Personality tendency",
            options=["All"] + sorted(admin_df["personality_tendency"].dropna().unique().tolist()),
            key="admin_tendency_filter",
        )
    with col3:
        search = st.text_input(
            "Search",
            placeholder="file name, email, skills",
            key="admin_search",
        )

    filtered_df = admin_df.copy()
    if category_filter != "All":
        filtered_df = filtered_df[filtered_df["predicted_category"] == category_filter]
    if tendency_filter != "All":
        filtered_df = filtered_df[filtered_df["personality_tendency"] == tendency_filter]
    if search:
        search_lower = search.lower()
        filtered_df = filtered_df[
            filtered_df.apply(
                lambda row: any(search_lower in str(value).lower() for value in row.values),
                axis=1,
            )
        ]

    render_history_table(filtered_df)

    with st.expander("View an individual analysis record"):
        if not filtered_df.empty:
            selected_upload = st.selectbox("Select upload ID", filtered_df["upload_id"].tolist())
            selected = next((record for record in records if record["upload_id"] == selected_upload), None)
            if selected:
                render_metric_row(selected)
                render_analysis_cards(selected)
                render_parsed_fields(selected.get("parsed_fields", {}))


def main() -> None:
    """Run the Streamlit application."""
    services = get_services()
    auth_service: AuthService = services["auth_service"]
    firestore_service: FirestoreService = services["firestore_service"]
    storage_service: StorageService = services["storage_service"]
    parser: ResumeParser = services["parser"]
    predictor: ResumePredictor = services["predictor"]

    user = st.session_state.get("user")
    if not user:
        user = handle_login(auth_service)
        if not user and not st.session_state.get("user"):
            st.stop()
    else:
        st.sidebar.success(f"Signed in as {user['email']}")
        if st.sidebar.button("Logout", use_container_width=True):
            st.session_state["user"] = None
            st.session_state["latest_results"] = []
            st.rerun()

    page = render_sidebar(is_admin=st.session_state["user"].get("is_admin", False))

    if page == "Upload & Analyze":
        render_upload_page(parser, predictor, storage_service, firestore_service, st.session_state["user"])
    elif page == "History":
        render_history_page(firestore_service, st.session_state["user"])
    elif page == "Admin Dashboard":
        render_admin_page(firestore_service, st.session_state["user"])


if __name__ == "__main__":
    main()
