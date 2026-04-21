"""Rule-based inference helpers for non-diagnostic personality tendency labels."""

from __future__ import annotations

from typing import List


def infer_personality_tendency(skills: List[str], experience: str, summary: str) -> str:
    """Infer a tendency label from resume content.

    This is intentionally a simple heuristic for demo purposes and must not be
    presented as a scientific personality assessment.
    """

    text = " ".join(skills + [experience or "", summary or ""]).lower()

    analytical_keywords = ["python", "sql", "machine learning", "finance", "analysis", "auditing"]
    people_keywords = ["recruitment", "hr", "talent", "communication", "leadership", "training"]
    creative_keywords = ["marketing", "seo", "content", "social media", "branding", "design"]
    structured_keywords = ["budgeting", "operations", "project management", "compliance", "excel"]

    if any(keyword in text for keyword in analytical_keywords):
        return "Analytical"
    if any(keyword in text for keyword in people_keywords):
        return "People-Oriented"
    if any(keyword in text for keyword in creative_keywords):
        return "Creative-Strategic"
    if any(keyword in text for keyword in structured_keywords):
        return "Organized-Structured"
    return "Balanced-Generalist"
