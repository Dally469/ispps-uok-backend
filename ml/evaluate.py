"""Print evaluation metrics for the trained model comparison.

Usage:
    python -m ml.evaluate
"""
from __future__ import annotations

import json
from pathlib import Path


METADATA_PATH = Path(__file__).resolve().parent / "artifacts" / "metadata.json"


def main():
    if not METADATA_PATH.exists():
        raise SystemExit("No metadata.json found. Run `python -m ml.train` first.")
    data = json.loads(METADATA_PATH.read_text())

    print(f"Trained at:          {data['trained_at']}")
    print(f"Train rows:          {data['n_train']}")
    print(f"Test rows:           {data['n_test']}")
    print(f"Selected classifier: {data['selected_classifier']}")
    print(f"Selection rule:      {data['selection_criterion']}\n")

    print("Class balance (train / test):")
    train_balance = data["class_balance"]["train"]
    test_balance = data["class_balance"]["test"]
    print(f"  pass=1: {train_balance.get('1', 0)} / {test_balance.get('1', 0)}")
    print(f"  pass=0: {train_balance.get('0', 0)} / {test_balance.get('0', 0)}\n")

    print("Regressor (predicted_grade):")
    for k, v in data["regressor_metrics"].items():
        print(f"  {k:>10}: {v}")

    print("\nClassifier comparison (dissertation 3.8):")
    print("  metrics column header key:")
    print("    acc = overall accuracy")
    print("    ar_rec / ar_f1 = recall / F1 on the at-risk class (3.8.3)")
    print("    p_rec / p_f1   = recall / F1 on the pass class")
    print("    auc            = ROC-AUC")
    print()
    header = (
        f"  {'model':>22}  {'acc':>6}  {'ar_rec':>7}  {'ar_f1':>6}  "
        f"{'p_rec':>6}  {'p_f1':>6}  {'auc':>6}"
    )
    print(header)
    print(
        f"  {'-'*22}  {'-'*6}  {'-'*7}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*6}"
    )
    for row in data["classifier_comparison"]:
        m = row["metrics"]
        marker = "*" if row["name"] == data["selected_classifier"] else " "
        auc = m.get("roc_auc")
        auc_str = f"{auc:.3f}" if auc is not None else "  -  "
        print(
            f" {marker}{row['name']:>22}  "
            f"{m['accuracy']:.3f}   "
            f"{m['at_risk_recall']:.3f}    "
            f"{m['at_risk_f1']:.3f}   "
            f"{m['recall']:.3f}   "
            f"{m['f1']:.3f}   "
            f"{auc_str}"
        )

    print("\nConfusion matrix (selected model):")
    selected = next(
        row for row in data["classifier_comparison"] if row["name"] == data["selected_classifier"]
    )
    cm = selected["metrics"]["confusion_matrix"]
    print(f"               predicted_fail  predicted_pass")
    print(f"  actual_fail        {cm['true_negative']:>6}          {cm['false_positive']:>6}")
    print(f"  actual_pass        {cm['false_negative']:>6}          {cm['true_positive']:>6}")

    print("\nTop 5 feature importances (RandomForest):")
    for row in data["feature_importances"][:5]:
        print(f"  {row['feature']:>22}  {row['importance']}")


if __name__ == "__main__":
    main()
