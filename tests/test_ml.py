"""ML module tests: features, predictor, and the 4-model trainer."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import pytest

from ml.features import (
    FEATURE_NAMES,
    StudentCourseFeatures,
    build_features,
    risk_from_score,
)
from ml.predict import StudentPredictor


# ── Plain dataclass-style helpers for feature building tests ────────────────

class _G:
    def __init__(self, score, max_score, atype="quiz"):
        self.score = score
        self.max_score = max_score
        self.assessment_type = atype


class _A:
    def __init__(self, status):
        self.status = status


# ── Feature engineering ─────────────────────────────────────────────────────

def test_feature_names_stable():
    assert FEATURE_NAMES == [
        "avg_score",
        "score_stddev",
        "min_score",
        "max_score",
        "num_assessments",
        "quiz_avg",
        "midterm_avg",
        "assignment_avg",
        "project_avg",
        "lab_avg",
        "attendance_rate",
        "absence_count",
        "late_count",
        "total_attendance_records",
        "credit_hours",
    ]


def test_build_features_empty_inputs():
    feats = build_features([], [])
    assert feats.avg_score == 0.0
    assert feats.attendance_rate == 0.0
    assert feats.num_assessments == 0
    assert feats.total_attendance_records == 0
    assert len(feats.to_vector()) == len(FEATURE_NAMES)


def test_build_features_aggregates():
    grades = [
        _G(80, 100, "quiz"),
        _G(60, 100, "quiz"),
        _G(70, 100, "assignment"),
        _G(90, 100, "midterm"),
    ]
    attendance = [_A("present")] * 8 + [_A("absent")] * 1 + [_A("late")] * 1
    feats = build_features(grades, attendance, credit_hours=4)
    assert feats.num_assessments == 4
    assert feats.avg_score == pytest.approx(75.0, abs=0.5)
    assert feats.quiz_avg == pytest.approx(70.0, abs=0.5)
    assert feats.midterm_avg == pytest.approx(90.0, abs=0.5)
    assert feats.attendance_rate == pytest.approx(80.0, abs=0.1)
    assert feats.absence_count == 1
    assert feats.late_count == 1
    assert feats.credit_hours == 4


def test_build_features_handles_zero_max_score():
    feats = build_features([_G(50, 0, "quiz")], [])
    assert feats.avg_score == 0.0  # divide-by-zero guarded


def test_risk_thresholds():
    # critical: grade<40 OR proba<0.25
    assert risk_from_score(35, 0.9) == "critical"
    assert risk_from_score(80, 0.10) == "critical"
    # high
    assert risk_from_score(50, 0.4) == "high"
    # medium
    assert risk_from_score(65, 0.6) == "medium"
    # low
    assert risk_from_score(90, 0.95) == "low"


# ── Trained-model artifacts ─────────────────────────────────────────────────

ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "ml" / "artifacts"


def test_model_artifact_present():
    """`python -m ml.train` must have been run before the suite."""
    assert (ARTIFACT_DIR / "model.joblib").exists(), (
        "Train the model first: python -m ml.train"
    )
    assert (ARTIFACT_DIR / "metadata.json").exists()


def test_metadata_has_4_model_comparison():
    meta = json.loads((ARTIFACT_DIR / "metadata.json").read_text())
    names = {row["name"] for row in meta["classifier_comparison"]}
    # Dissertation 3.7: DT + RF + LR + SVM
    assert names == {"decision_tree", "random_forest", "logistic_regression", "svm"}

    # Every row reports the metrics required by section 3.8 plus the
    # at-risk-class variants used for selection per 3.7.6.
    required = {
        "accuracy", "precision", "recall", "f1", "confusion_matrix",
        "at_risk_precision", "at_risk_recall", "at_risk_f1",
    }
    for row in meta["classifier_comparison"]:
        assert required <= set(row["metrics"]), row


def test_metadata_selected_by_at_risk_recall_first():
    """Dissertation 3.7.6 says recall is critical because the system's
    purpose is identifying at-risk students. We therefore select on the
    at-risk class (pos_label=0), not the pass class."""
    meta = json.loads((ARTIFACT_DIR / "metadata.json").read_text())
    selected_name = meta["selected_classifier"]
    selected = next(r for r in meta["classifier_comparison"] if r["name"] == selected_name)
    selected_recall = selected["metrics"]["at_risk_recall"]
    for row in meta["classifier_comparison"]:
        assert row["metrics"]["at_risk_recall"] <= selected_recall + 1e-9


def test_model_bundle_has_required_keys():
    bundle = joblib.load(ARTIFACT_DIR / "model.joblib")
    assert {"regressor", "classifier", "classifier_name", "feature_names"} <= set(bundle)
    assert bundle["feature_names"] == FEATURE_NAMES


# ── End-to-end predict ──────────────────────────────────────────────────────

def test_predictor_runtime():
    predictor = StudentPredictor.get()
    feats = build_features(
        [_G(80, 100, "quiz"), _G(70, 100, "midterm"), _G(75, 100, "assignment")],
        [_A("present")] * 9 + [_A("absent")] * 1,
    )
    out = predictor.predict(feats)
    assert 0 <= out["predicted_grade"] <= 100
    assert 0 <= out["pass_probability"] <= 1
    assert out["risk_level"] in ("low", "medium", "high", "critical")
    assert out["factors"] and len(out["factors"]) == 5
    assert out["recommendations"]
    assert out["summary"]
