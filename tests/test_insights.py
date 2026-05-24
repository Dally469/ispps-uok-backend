"""Insights router: summary, study-plan, risk-scan."""
from __future__ import annotations

from tests.conftest import OTHER_STUDENT_ID, SCHOOL_ID, STUDENT_ID


async def test_summary_for_student(client, admin_headers):
    r = await client.post(
        "/api/insights/summary",
        json={"student_id": STUDENT_ID},
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "summary" in body
    assert "features" in body
    # Feature dict comes from build_features.to_dict()
    assert "avg_score" in body["features"]
    assert "attendance_rate" in body["features"]


async def test_summary_for_student_with_no_grades(client, admin_headers):
    # Student f0...004 had no grades originally - but ML backfill gave
    # them grades via their enrollments. Use a brand-new student to
    # provoke the 422.
    # We create one and immediately ask for a summary.
    import uuid

    create = await client.post(
        "/api/students",
        json={
            "school_id": SCHOOL_ID,
            "student_number": f"BLANK-{uuid.uuid4().hex[:8]}",
        },
        headers=admin_headers,
    )
    sid = create.json()["id"]
    r = await client.post(
        "/api/insights/summary",
        json={"student_id": sid},
        headers=admin_headers,
    )
    assert r.status_code == 422


async def test_study_plan(client, admin_headers):
    r = await client.post(
        "/api/insights/study-plan",
        json={"student_id": STUDENT_ID},
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "plan" in body
    assert "Study Plan" in body["plan"]


async def test_risk_scan_admin(client, admin_headers):
    r = await client.get(
        f"/api/insights/risk-scan?school_id={SCHOOL_ID}", headers=admin_headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert {"total", "atRisk", "critical", "warnings"} <= set(body)
    assert body["total"] >= 1
    # At least one warning expected given the failing seed profiles
    for w in body["warnings"]:
        assert w["riskLevel"] in ("medium", "high", "critical")


async def test_risk_scan_blocked_for_student(client, student_headers):
    r = await client.get(
        f"/api/insights/risk-scan?school_id={SCHOOL_ID}", headers=student_headers
    )
    assert r.status_code == 403


async def test_student_cannot_get_other_summary(client, student_headers):
    r = await client.post(
        "/api/insights/summary",
        json={"student_id": OTHER_STUDENT_ID},
        headers=student_headers,
    )
    assert r.status_code == 404
