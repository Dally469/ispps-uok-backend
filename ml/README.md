# ISPPS — Machine Learning Pipeline

Self-trained student performance prediction model. **No third-party LLM is used.**

## What it does

For each `(student, course)` pair we build a feature vector from grade and
attendance history and train two scikit-learn models:

| Head        | Algorithm                | Output                       |
|-------------|--------------------------|------------------------------|
| Regressor   | `RandomForestRegressor`  | `predicted_grade` (0–100)    |
| Classifier  | `RandomForestClassifier` | `pass_probability` + `risk`  |

The risk level (`low`, `medium`, `high`, `critical`) is derived from both
heads via [`features.risk_from_score`](features.py).

## Files

| File          | Purpose                                                   |
|---------------|-----------------------------------------------------------|
| `features.py` | Feature definitions and engineering (15 features).        |
| `dataset.py`  | Pulls enrollments from the DB and builds `(X, y)`.        |
| `train.py`    | Trains both models, saves to `artifacts/model.joblib`.    |
| `evaluate.py` | Prints metrics from `artifacts/metadata.json`.            |
| `predict.py`  | Singleton `StudentPredictor` used by the API at runtime.  |

## Run

```bash
# from the backend/ directory, with your venv active and DB seeded
python -m ml.train      # trains and saves artifacts/
python -m ml.evaluate   # prints metrics + top feature importances
```

The trained artifact is loaded lazily the first time
[`app/api/predictions.py`](../app/api/predictions.py) needs it.

## Adding a new feature

1. Add the field to `FEATURE_NAMES` and `StudentCourseFeatures` in `features.py`.
2. Populate it inside `build_features`.
3. Re-run `python -m ml.train`.
