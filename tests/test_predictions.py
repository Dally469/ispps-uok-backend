"""Predictions router: list / generate / manual create."""
from __future__ import annotations

import uuid

from tests.conftest import (
    DSA_COURSE_ID,
    OTHER_STUDENT_ID,
    STUDENT_ID,
)


# ── List ─────────────────────────────────────────────────────────────────────

async def test_admin_lists_predictions(client, admin_headers):
    r = await client.get("/api/predictions?limit=100", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    # 12 predictions seeded
    assert len(body) >= 12
    for p in body:
        assert {"id", "student_id", "predicted_grade", "pass_probability", "risk_level"} <= set(p)


async def test_student_only_sees_own_predictions(client, student_headers):
    r = await client.get("/api/predictions?limit=100", headers=student_headers)
    assert r.status_code == 200
    for p in r.json():
        assert p["student_id"] == STUDENT_ID


async def test_lecturer_sees_predictions_for_own_courses(client, lecturer_headers):
    """Dr. Silva owns DSA + Calculus II. She should see predictions
    tied to her courses, plus general overall predictions for students
    enrolled in her courses."""
    r = await client.get("/api/predictions?limit=100", headers=lecturer_headers)
    assert r.status_code == 200
    # at least one prediction visible (seed has predictions across roles)
    assert len(r.json()) >= 1


async def test_filter_by_risk(client, admin_headers):
    r = await client.get("/api/predictions?risk_level=high", headers=admin_headers)
    assert r.status_code == 200
    for p in r.json():
        assert p["risk_level"] == "high"


async def test_filter_by_predicted_grade(client, admin_headers):
    r = await client.get(
        "/api/predictions?min_predicted_grade=80", headers=admin_headers
    )
    assert r.status_code == 200
    for p in r.json():
        assert p["predicted_grade"] >= 80


# ── Generate (real ML model) ─────────────────────────────────────────────────

async def test_generate_prediction_runs_model(client, admin_headers):
    """Hits the live trained model. Requires `python -m ml.train` to
    have run successfully before the test session."""
    payload = {"student_id": STUDENT_ID, "course_id": DSA_COURSE_ID}
    r = await client.post(
        "/api/predictions/generate", json=payload, headers=admin_headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["risk_level"] in ("low", "medium", "high", "critical")
    assert 0 <= body["pass_probability"] <= 1
    assert 0 <= body["predicted_grade"] <= 100
    assert body["factors"], "factors list should be non-empty"
    assert body["recommendations"], "recommendations list should be non-empty"
    assert body["ai_summary"]


async def test_generate_unknown_student(client, admin_headers):
    r = await client.post(
        "/api/predictions/generate",
        json={"student_id": str(uuid.uuid4())},
        headers=admin_headers,
    )
    assert r.status_code == 404


async def test_student_cannot_generate_for_other(client, student_headers):
    r = await client.post(
        "/api/predictions/generate",
        json={"student_id": OTHER_STUDENT_ID},
        headers=student_headers,
    )
    # not visible -> 404
    assert r.status_code == 404


# ── Manual create ────────────────────────────────────────────────────────────

async def test_manual_create_prediction(client, admin_headers):
    payload = {
        "student_id": STUDENT_ID,
        "course_id": DSA_COURSE_ID,
        "predicted_grade": 72.5,
        "pass_probability": 0.81,
        "risk_level": "low",
        "factors": [{"name": "avg_score", "score": 75, "impact": "positive"}],
        "recommendations": ["Keep momentum."],
        "ai_summary": "Solid student.",
    }
    r = await client.post("/api/predictions", json=payload, headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["predicted_grade"] == 72.5
    assert body["risk_level"] == "low"


async def test_student_cannot_manual_create_for_other(client, student_headers):
    r = await client.post(
        "/api/predictions",
        json={
            "student_id": OTHER_STUDENT_ID,
            "predicted_grade": 50,
            "pass_probability": 0.5,
            "risk_level": "medium",
        },
        headers=student_headers,
    )
    # student_visibility_clause restricts -> 404
    assert r.status_code == 404
