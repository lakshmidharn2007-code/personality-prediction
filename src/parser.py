"""Resume parsing helpers for PDF and DOCX documents."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Dict, List

import docx
import nltk
import pdfplumber

from src.utils import clean_text


COMMON_SKILLS = {
    "python",
    "sql",
    "excel",
    "tableau",
    "power bi",
    "machine learning",
    "data analysis",
    "recruitment",
    "payroll",
    "leadership",
    "communication",
    "project management",
    "digital marketing",
    "seo",
    "sem",
    "content writing",
    "social media",
    "accounting",
    "financial modeling",
    "budgeting",
    "auditing",
    "java",
    "c++",
    "aws",
    "docker",
    "kubernetes",
    "hr operations",
    "talent acquisition",
}


@dataclass
class ResumeParser:
    """Extract and parse resume details from uploaded files."""

    def __post_init__(self) -> None:
        for package in ("punkt", "stopwords"):
            try:
                nltk.data.find(f"tokenizers/{package}" if package == "punkt" else f"corpora/{package}")
            except LookupError:
                nltk.download(package, quiet=True)

    def extract_text_from_upload(self, uploaded_file) -> str:
        """Extract text from a Streamlit uploaded file."""
        file_name = uploaded_file.name.lower()
        file_bytes = uploaded_file.getvalue()

        if file_name.endswith(".pdf"):
            return self._extract_text_from_pdf(file_bytes)
        if file_name.endswith(".docx"):
            return self._extract_text_from_docx(file_bytes)

        raise ValueError(f"Unsupported file format for `{uploaded_file.name}`.")

    def _extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """Extract text from a PDF file."""
        text_chunks: List[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_chunks.append(page_text)
        return "\n".join(text_chunks).strip()

    def _extract_text_from_docx(self, file_bytes: bytes) -> str:
        """Extract text from a DOCX file."""
        document = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text).strip()

    def parse_resume(self, text: str) -> Dict[str, object]:
        """Parse high-value fields from resume text."""
        cleaned = clean_text(text)
        return {
            "name": self._extract_name(text),
            "email": self._extract_email(text),
            "phone": self._extract_phone(text),
            "skills": self._extract_skills(cleaned),
            "education": self._extract_section(text, ["education", "academic background"]),
            "experience": self._extract_section(text, ["experience", "work experience", "employment history"]),
            "summary": self._extract_section(text, ["summary", "profile", "professional summary", "objective"]),
        }

    def _extract_name(self, text: str) -> str:
        """Infer candidate name from the top lines of the resume."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:5]:
            if not re.search(r"@|\d|resume|curriculum vitae", line.lower()):
                if 2 <= len(line.split()) <= 4:
                    return line.title()
        return "Not found"

    def _extract_email(self, text: str) -> str:
        match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
        return match.group(0) if match else "Not found"

    def _extract_phone(self, text: str) -> str:
        match = re.search(r"(\+?\d[\d\s().-]{8,}\d)", text)
        if not match:
            return "Not found"
        return re.sub(r"\s+", " ", match.group(0)).strip()

    def _extract_skills(self, cleaned_text: str) -> List[str]:
        lowered = cleaned_text.lower()
        matched = sorted(skill for skill in COMMON_SKILLS if skill in lowered)
        return matched

    def _extract_section(self, text: str, headings: List[str]) -> str:
        """Extract a coarse section by heading name."""
        normalized = text.replace("\r", "\n")
        pattern = re.compile(
            rf"(?is)({'|'.join(re.escape(heading) for heading in headings)})\s*[:\-]?\s*(.*?)(?:\n[A-Z][A-Za-z /\-&]{{2,}}[:\-]|\Z)"
        )
        match = pattern.search(normalized)
        if match:
            value = re.sub(r"\n{2,}", "\n", match.group(2)).strip()
            return value or "Not found"
        return "Not found"
