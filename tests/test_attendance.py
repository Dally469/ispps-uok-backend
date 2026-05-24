"""Attendance router: list/create/bulk."""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from tests.conftest import (
    DSA_COURSE_ID,
    DBMS_COURSE_ID,
    ENROLLMENT_ID,
    STUDENT_ID,
)


async def test_admin_lists_attendance(client, admin_headers):
    r = await client.get("/api/attendance?limit=200", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body) >= 30  # seed has 50+ attendance rows
    assert "status" in body[0]
    assert "enrollment" in body[0]


async def test_filter_attendance_by_status(client, admin_headers):
    r = await client.get(
        "/api/attendance?status=absent&limit=200", headers=admin_headers
    )
    assert r.status_code == 200
    for rec in r.json():
        assert rec["status"] == "absent"


async def test_filter_attendance_by_student(client, admin_headers):
    r = await client.get(
        f"/api/attendance?student_id={STUDENT_ID}&limit=200",
        headers=admin_headers,
    )
    assert r.status_code == 200
    # All returned rows belong to that student
    body = r.json()
    for rec in body:
        # Student id is reachable via the enrollment payload
        assert rec["enrollment"]["student"]["id"] == STUDENT_ID


async def test_student_sees_only_own_attendance(client, student_headers):
    r = await client.get("/api/attendance?limit=200", headers=student_headers)
    assert r.status_code == 200
    for rec in r.json():
        assert rec["enrollment"]["student"]["id"] == STUDENT_ID


async def test_admin_creates_attendance(client, admin_headers):
    payload = {
        "enrollment_id": ENROLLMENT_ID,
        "date": str(date.today() + timedelta(days=-uuid.uuid4().int % 365)),
        "status": "present",
        "note": "auto-test",
    }
    r = await client.post("/api/attendance", json=payload, headers=admin_headers)
    # Uniqueness on (enrollment_id, date) - retry with a date unlikely to clash
    if r.status_code == 500:
        payload["date"] = "2027-04-01"
        r = await client.post("/api/attendance", json=payload, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "present"


async def test_student_cannot_create_attendance(client, student_headers):
    r = await client.post(
        "/api/attendance",
        json={
            "enrollment_id": ENROLLMENT_ID,
            "date": "2027-04-15",
            "status": "present",
        },
        headers=student_headers,
    )
    assert r.status_code == 403


async def test_lecturer_create_for_own_course(client, lecturer_headers):
    # Dr. Silva owns DSA - enrollment bb...001 is DSA
    r = await client.post(
        "/api/attendance",
        json={
            "enrollment_id": ENROLLMENT_ID,
            "date": "2027-05-12",
            "status": "late",
        },
        headers=lecturer_headers,
    )
    assert r.status_code == 200, r.text


async def test_lecturer_blocked_from_other_course(client, lecturer_headers):
    # bb...002 is a DBMS enrollment owned by Dr. Perera, not Dr. Silva
    r = await client.post(
        "/api/attendance",
        json={
            "enrollment_id": "bb000000-0000-0000-0000-000000000002",
            "date": "2027-05-15",
            "status": "present",
        },
        headers=lecturer_headers,
    )
    assert r.status_code == 403


async def test_bulk_attendance_upsert(client, admin_headers):
    payload = {
        "course_id": DSA_COURSE_ID,
        "date": "2027-06-01",
        "records": [
            {"enrollment_id": ENROLLMENT_ID, "status": "present"},
        ],
    }
    r = await client.post(
        "/api/attendance/bulk", json=payload, headers=admin_headers
    )
    assert r.status_code == 200, r.text
    assert r.json()["inserted"] == 1

    # Re-running with a different status should upsert (no constraint error)
    payload["records"][0]["status"] = "absent"
    r2 = await client.post(
        "/api/attendance/bulk", json=payload, headers=admin_headers
    )
    assert r2.status_code == 200


async def test_bulk_attendance_filters_invalid_enrollments(client, admin_headers):
    # The fake enrollment ID is not enrolled in DSA -> should be filtered out
    payload = {
        "course_id": DSA_COURSE_ID,
        "date": "2027-06-15",
        "records": [
            {"enrollment_id": str(uuid.uuid4()), "status": "present"},
        ],
    }
    r = await client.post(
        "/api/attendance/bulk", json=payload, headers=admin_headers
    )
    assert r.status_code == 400
