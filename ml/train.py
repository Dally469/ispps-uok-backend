"""Train ISPPS prediction models per the dissertation methodology.

The book (Chapter Three, sections 3.7-3.8) requires comparing four
classifiers - Decision Tree, Random Forest, Logistic Regression, and
SVM - against accuracy, precision, recall, F1, and the confusion matrix.
Recall is treated as the primary selection criterion because the
practical cost of missing an at-risk student outweighs the cost of a
false positive (3.7.6).

A grade RandomForestRegressor is also trained for the predicted-grade
output the API surfaces (it is not part of the four-way classifier
comparison - only the pass/fail head is).

Usage:
    python -m ml.train
"""
from __future__ import annotations

import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from ml.dataset import build_dataframe, split_xy
from ml.features import FEATURE_NAMES


ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "model.joblib"
METADATA_PATH = ARTIFACT_DIR / "metadata.json"

RANDOM_STATE = 42

# 3.7.6 — recall is the primary selection criterion because the practical
# cost of missing an at-risk student outweighs a false alarm. The
# downstream API still exposes pass_probability (predict_proba[:,1]) for
# clarity, but the model selection rule operates on the *at-risk* class
# (label 0 = fail) so the chosen classifier is the one best at catching
# the students the dissertation cares about.
SELECTION_KEY = ("at_risk_recall", "f1")


def _candidate_classifiers() -> dict[str, object]:
    """The four models named in the dissertation (3.7.1-3.7.4)."""
    return {
        "decision_tree": DecisionTreeClassifier(
            max_depth=6,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_leaf=2,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        # Logistic regression and SVM need feature scaling. We pipe a
        # StandardScaler in front of each so the model selection is
        # apples-to-apples with the tree-based ones (which are
        # scale-invariant).
        "logistic_regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
        "svm": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    SVC(
                        kernel="rbf",
                        C=1.0,
                        gamma="scale",
                        probability=True,
                        class_weight="balanced",
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
    }


def _score(y_true, y_pred, y_proba) -> dict:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    # confusion_matrix layout: [[TN, FP], [FN, TP]] where positive=1 (pass).
    tn, fp, fn, tp = cm.ravel()
    metrics = {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        # Metrics on the pass class (label=1) - what the downstream API
        # implicitly reports via pass_probability.
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        # Metrics on the at-risk class (label=0) - the dissertation's
        # primary identification goal (sections 3.7.6, 3.8.3).
        "at_risk_precision": round(
            float(precision_score(y_true, y_pred, pos_label=0, zero_division=0)), 4
        ),
        "at_risk_recall": round(
            float(recall_score(y_true, y_pred, pos_label=0, zero_division=0)), 4
        ),
        "at_risk_f1": round(
            float(f1_score(y_true, y_pred, pos_label=0, zero_division=0)), 4
        ),
        "confusion_matrix": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
    }
    if y_proba is not None and len(set(y_true)) > 1:
        try:
            metrics["roc_auc"] = round(float(roc_auc_score(y_true, y_proba)), 4)
        except ValueError:
            metrics["roc_auc"] = None
    else:
        metrics["roc_auc"] = None
    return metrics


def _proba(model, X) -> np.ndarray | None:
    if hasattr(model, "predict_proba"):
        try:
            return model.predict_proba(X)[:, 1]
        except Exception:
            return None
    if hasattr(model, "decision_function"):
        try:
            return model.decision_function(X)
        except Exception:
            return None
    return None


def _pick_best(comparisons: list[dict]) -> dict:
    """Pick by recall first, then F1 (3.7.6 — recall is critical)."""
    return max(
        comparisons,
        key=lambda c: tuple(c["metrics"].get(k, 0.0) or 0.0 for k in SELECTION_KEY),
    )


def train():
    print("Loading data from database...")
    df = build_dataframe()
    print(f"  -> {len(df)} training rows")

    X, y_grade, y_pass = split_xy(df)
    stratify = y_pass if len(set(y_pass)) > 1 else None
    X_train, X_test, yg_train, yg_test, yp_train, yp_test = train_test_split(
        X, y_grade, y_pass, test_size=0.2, random_state=RANDOM_STATE, stratify=stratify
    )

    # ── Regressor (predicted_grade head) ─────────────────────────────
    print("\nTraining grade regressor (RandomForestRegressor)...")
    regressor = RandomForestRegressor(
        n_estimators=200,
        max_depth=12,
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    regressor.fit(X_train, yg_train)
    yg_pred = regressor.predict(X_test)
    reg_metrics = {
        "mae": round(float(mean_absolute_error(yg_test, yg_pred)), 4),
        "r2": round(float(r2_score(yg_test, yg_pred)), 4),
    }

    # ── Classifier shootout (DT / RF / LR / SVM) ─────────────────────
    print("\nTraining and comparing classifiers (DT / RF / LR / SVM)...")
    comparisons: list[dict] = []
    fitted: dict[str, object] = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # keep terminal output tidy
        for name, clf in _candidate_classifiers().items():
            clf.fit(X_train, yp_train)
            y_pred = clf.predict(X_test)
            y_proba = _proba(clf, X_test)
            metrics = _score(yp_test, y_pred, y_proba)
            comparisons.append({"name": name, "metrics": metrics})
            fitted[name] = clf
            print(
                f"  {name:>22}  "
                f"acc={metrics['accuracy']:.3f}  "
                f"at-risk_rec={metrics['at_risk_recall']:.3f}  "
                f"at-risk_f1={metrics['at_risk_f1']:.3f}  "
                f"pass_f1={metrics['f1']:.3f}"
            )

    best = _pick_best(comparisons)
    best_name = best["name"]
    classifier = fitted[best_name]
    print(f"\nSelected classifier: {best_name} (highest at-risk recall, F1 tie-break)")

    # ── Feature importance (use RF for stable importances) ───────────
    rf_for_importance = fitted["random_forest"]
    importances = sorted(
        zip(FEATURE_NAMES, rf_for_importance.feature_importances_),
        key=lambda kv: kv[1],
        reverse=True,
    )

    # ── Persist artifacts ────────────────────────────────────────────
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "regressor": regressor,
            "classifier": classifier,
            "classifier_name": best_name,
            "feature_names": FEATURE_NAMES,
        },
        MODEL_PATH,
    )

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "class_balance": {
            "train": {int(k): int(v) for k, v in zip(*np.unique(yp_train, return_counts=True))},
            "test": {int(k): int(v) for k, v in zip(*np.unique(yp_test, return_counts=True))},
        },
        "selected_classifier": best_name,
        "selection_criterion": "at-risk recall (pos_label=0), tie-broken by F1 (dissertation 3.7.6)",
        "regressor_metrics": reg_metrics,
        "classifier_comparison": comparisons,
        "feature_importances": [
            {"feature": k, "importance": round(float(v), 4)} for k, v in importances
        ],
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2))

    print(f"\nSaved model    -> {MODEL_PATH}")
    print(f"Saved metadata -> {METADATA_PATH}")


if __name__ == "__main__":
    train()
