"""Model loading and flexible prediction helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List

import joblib
import numpy as np
import streamlit as st

from src.rules import infer_personality_tendency


@st.cache_resource(show_spinner=False)
def load_model_from_path(model_path: str):
    """Load and cache the persisted model pipeline by path."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model file not found at `{model_path}`. "
            "Place your joblib model there or set MODEL_PATH."
        )
    return joblib.load(model_path)


@dataclass
class ResumePredictor:
    """Predict either resume category or personality depending on the loaded model."""

    model_path: str | None = None

    def __post_init__(self) -> None:
        self.model_path = self.model_path or self._resolve_model_path()
        self.model = load_model_from_path(self.model_path)

    def _resolve_model_path(self) -> str:
        if hasattr(st, "secrets") and "MODEL_PATH" in st.secrets:
            return st.secrets["MODEL_PATH"]
        return os.getenv("MODEL_PATH", "models/resume_classifier.joblib")

    def predict(self, raw_text: str) -> Dict[str, float]:
        """Predict the primary label and classify the model output type.

        Supports both single-output classifiers and multi-output Big Five
        models where `predict` returns one value per OCEAN trait.
        """
        prediction_output = self.model.predict([raw_text])
        predicted_label = prediction_output[0]
        raw_classes = getattr(self.model, "classes_", [])

        if self._is_multi_output_prediction(predicted_label, raw_classes):
            return self._predict_big5(raw_text, predicted_label, raw_classes)

        classes = [str(label) for label in raw_classes]
        prediction_type = self._infer_prediction_type(classes)
        confidence = 1.0
        top_scores: List[Dict[str, float]] = []

        if hasattr(self.model, "predict_proba"):
            probabilities = np.asarray(self.model.predict_proba([raw_text])[0], dtype=float).ravel()
            confidence = float(np.max(probabilities))
            ranked_indices = np.argsort(probabilities)[::-1]
            top_scores = [
                {
                    "label": str(classes[int(index)]) if int(index) < len(classes) else f"class_{int(index)}",
                    "score": round(float(probabilities[int(index)]), 4),
                }
                for index in ranked_indices[:5]
            ]

        return {
            "prediction_type": prediction_type,
            "primary_label": str(predicted_label),
            "confidence": round(confidence, 4),
            "model_labels": classes,
            "top_scores": top_scores,
            "personality_profile": {},
        }

    def infer_personality_tendency(self, skills: List[str], experience: str, summary: str) -> str:
        """Return a transparent, rule-based tendency label."""
        return infer_personality_tendency(skills=skills, experience=experience, summary=summary)

    def _infer_prediction_type(self, classes: List[str]) -> str:
        """Infer whether the model predicts resume categories or personality labels."""
        normalized = {label.strip().lower() for label in classes}
        category_labels = {"finance", "hr", "it", "marketing"}
        ocean_keywords = {
            "openness",
            "conscientiousness",
            "extraversion",
            "agreeableness",
            "neuroticism",
            "o",
            "c",
            "e",
            "a",
            "n",
        }

        if normalized and normalized.issubset(category_labels):
            return "resume_category"
        if normalized & ocean_keywords:
            return "personality"
        return "unknown"

    def _is_multi_output_prediction(self, predicted_label, raw_classes) -> bool:
        """Return True when model output looks like five OCEAN trait outputs."""
        if isinstance(raw_classes, list) and len(raw_classes) >= 5:
            return True
        if isinstance(raw_classes, np.ndarray) and raw_classes.dtype == object and len(raw_classes) >= 5:
            return True
        if isinstance(predicted_label, (list, tuple, np.ndarray)) and np.asarray(predicted_label).ndim > 0:
            return len(np.asarray(predicted_label).ravel()) >= 5
        return False

    def _predict_big5(self, raw_text: str, predicted_label, raw_classes) -> Dict[str, object]:
        """Convert a multi-output Big Five prediction into UI-friendly fields."""
        trait_names = [
            "Openness",
            "Conscientiousness",
            "Extraversion",
            "Agreeableness",
            "Neuroticism",
        ]
        predicted_values = np.asarray(predicted_label).ravel().tolist()
        profile: Dict[str, object] = {}
        top_scores: List[Dict[str, float]] = []

        if hasattr(self.model, "predict_proba"):
            probabilities = self.model.predict_proba([raw_text])
        else:
            probabilities = None

        for index, trait_name in enumerate(trait_names):
            predicted_value = predicted_values[index] if index < len(predicted_values) else None
            trait_score = self._trait_score_from_output(probabilities, index, predicted_value)
            profile[trait_name] = {
                "prediction": self._format_trait_value(predicted_value),
                "score": round(float(trait_score), 4),
            }
            top_scores.append({"label": trait_name, "score": round(float(trait_score), 4)})

        top_scores = sorted(top_scores, key=lambda item: item["score"], reverse=True)
        dominant_trait = top_scores[0]["label"] if top_scores else "Big Five Personality"
        confidence = top_scores[0]["score"] if top_scores else 1.0

        return {
            "prediction_type": "personality",
            "primary_label": dominant_trait,
            "confidence": round(float(confidence), 4),
            "model_labels": self._serialize_classes(raw_classes),
            "top_scores": top_scores,
            "personality_profile": profile,
        }

    def _trait_score_from_output(self, probabilities, index: int, predicted_value) -> float:
        """Choose the score for a Big Five trait from probabilities or raw output."""
        if probabilities is not None and isinstance(probabilities, list) and index < len(probabilities):
            trait_probabilities = np.asarray(probabilities[index][0], dtype=float).ravel()
            if trait_probabilities.size == 0:
                return 0.0
            if trait_probabilities.size == 2:
                return float(trait_probabilities[1])
            return float(np.max(trait_probabilities))

        try:
            numeric_value = float(predicted_value)
        except (TypeError, ValueError):
            return 1.0

        if numeric_value > 1:
            return max(0.0, min(numeric_value / 100.0, 1.0))
        return max(0.0, min(numeric_value, 1.0))

    def _format_trait_value(self, value) -> str:
        """Convert raw model output into a readable trait value."""
        if value is None:
            return "Unknown"
        if isinstance(value, (np.integer, int)):
            return "High" if int(value) == 1 else "Low"
        if isinstance(value, (np.floating, float)):
            return f"{float(value):.2f}"
        return str(value)

    def _serialize_classes(self, raw_classes) -> List[str]:
        """Convert sklearn `classes_` from single or multi-output models to strings."""
        if isinstance(raw_classes, list):
            return [", ".join(str(item) for item in np.asarray(classes).ravel()) for classes in raw_classes]
        if isinstance(raw_classes, np.ndarray) and raw_classes.dtype == object:
            return [", ".join(str(item) for item in np.asarray(classes).ravel()) for classes in raw_classes]
        return [str(label) for label in np.asarray(raw_classes).ravel()]
