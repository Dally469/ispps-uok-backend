"""Runtime inference — loads the trained model once and exposes predict()."""
from __future__ import annotations

from pathlib import Path
from threading import Lock

import joblib

from ml.features import FEATURE_NAMES, StudentCourseFeatures, risk_from_score


DEFAULT_ARTIFACT = Path(__file__).resolve().parent / "artifacts" / "model.joblib"


class StudentPredictor:
    _instance: "StudentPredictor | None" = None
    _lock = Lock()

    def __init__(self, artifact_path: Path | str = DEFAULT_ARTIFACT):
        self.artifact_path = Path(artifact_path)
        if not self.artifact_path.exists():
            raise FileNotFoundError(
                f"Model artifact not found at {self.artifact_path}. "
                "Run `python -m ml.train` to create it."
            )
        bundle = joblib.load(self.artifact_path)
        self.regressor = bundle["regressor"]
        self.classifier = bundle["classifier"]
        self.feature_names: list[str] = bundle["feature_names"]
        if self.feature_names != FEATURE_NAMES:
            raise RuntimeError(
                "Model feature names do not match current ml.features. "
                "Retrain after changing the feature set."
            )

    @classmethod
    def get(cls) -> "StudentPredictor":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def predict(self, features: StudentCourseFeatures) -> dict:
        vector = [features.to_vector()]
        predicted_grade = float(self.regressor.predict(vector)[0])
        pass_proba = float(self.classifier.predict_proba(vector)[0][1])
        risk_level = risk_from_score(predicted_grade, pass_proba)

        importances = self.regressor.feature_importances_
        contributions = sorted(
            zip(FEATURE_NAMES, features.to_vector(), importances),
            key=lambda t: t[2],
            reverse=True,
        )[:5]
        factors = [
            {
                "name": name,
                "score": round(float(value), 2),
                "weight": round(float(weight), 3),
                "impact": _impact(name, value),
            }
            for name, value, weight in contributions
        ]

        recommendations = _recommendations(features, predicted_grade, pass_proba)

        return {
            "predicted_grade": round(max(0.0, min(100.0, predicted_grade)), 2),
            "pass_probability": round(max(0.0, min(1.0, pass_proba)), 3),
            "risk_level": risk_level,
            "factors": factors,
            "recommendations": recommendations,
            "summary": _summary(features, predicted_grade, pass_proba, risk_level),
        }


def _impact(name: str, value: float) -> str:
    if name in {"absence_count", "late_count", "score_stddev"}:
        if value <= 1:
            return "positive"
        if value >= 5:
            return "negative"
        return "neutral"
    if value >= 75:
        return "positive"
    if value < 50:
        return "negative"
    return "neutral"


def _recommendations(f: StudentCourseFeatures, predicted_grade: float, pass_proba: float) -> list[str]:
    tips: list[str] = []
    if f.attendance_rate < 80:
        tips.append("Improve class attendance — target at least 90%.")
    if f.avg_score < 60:
        tips.append("Schedule weekly study sessions on weakest subjects.")
    if f.score_stddev > 15:
        tips.append("Performance is inconsistent — revisit study planning and time management.")
    if f.assignment_avg and f.assignment_avg < 60:
        tips.append("Strengthen assignment work — start earlier and seek feedback.")
    if f.quiz_avg and f.quiz_avg < 60:
        tips.append("Use spaced-repetition revision to lift quiz scores.")
    if pass_proba < 0.5:
        tips.append("Meet with the course lecturer to plan an intervention.")
    if not tips:
        tips.append("Maintain current study habits and attendance.")
    return tips[:5]


def _summary(f: StudentCourseFeatures, grade: float, pass_proba: float, risk: str) -> str:
    return (
        f"Predicted final grade {grade:.1f}% with {pass_proba*100:.0f}% pass probability "
        f"(risk: {risk}). Based on {f.num_assessments} assessments and "
        f"{f.total_attendance_records} attendance records."
    )
