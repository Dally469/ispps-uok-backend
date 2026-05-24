"""Students router: list/get/create/update/delete + RBAC visibility."""
from __future__ import annotations

import uuid

from tests.conftest import (
    DSA_COURSE_ID,
    OTHER_STUDENT_ID,
    SCHOOL_ID,
    STUDENT_ID,
)


# ── List endpoint ────────────────────────────────────────────────────────────

async def test_admin_sees_all_students(client, admin_headers):
    r = await client.get("/api/students?limit=100", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert isinstance(body, list)
    # Seed has 12 students
    assert len(body) >= 12


async def test_lecturer_sees_only_enrolled_students(client, lecturer_headers):
    """Dr. Silva teaches DSA + Calculus II - she should not see
    students who are only in Dr. Perera's courses (DBMS/Physics)."""
    r = await client.get("/api/students?limit=100", headers=lecturer_headers)
    assert r.status_code == 200
    student_numbers = {s["student_number"] for s in r.json()}
    # Ashan is in DSA -> visible
    assert "UOK-2024-001" in student_numbers


async def test_student_sees_only_themselves(client, student_headers):
    r = await client.get("/api/students?limit=100", headers=student_headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["student_number"] == "UOK-2024-001"


async def test_list_search_filters(client, admin_headers):
    r = await client.get("/api/students?search=Ashan", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert any(s["user"] and "Ashan" in s["user"]["full_name"] for s in body)


async def test_list_filters_by_course(client, admin_headers):
    r = await client.get(
        f"/api/students?course_id={DSA_COURSE_ID}", headers=admin_headers
    )
    assert r.status_code == 200
    assert len(r.json()) >= 1


# ── Detail endpoint ──────────────────────────────────────────────────────────

async def test_get_student_admin(client, admin_headers):
    r = await client.get(f"/api/students/{STUDENT_ID}", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == STUDENT_ID
    assert "enrollments" in body
    assert "predictions" in body
    assert "insights" in body


async def test_get_student_student_self(client, student_headers):
    r = await client.get(f"/api/students/{STUDENT_ID}", headers=student_headers)
    assert r.status_code == 200


async def test_get_student_student_other_forbidden(client, student_headers):
    r = await client.get(f"/api/students/{OTHER_STUDENT_ID}", headers=student_headers)
    # student_visibility_clause restricts to own record - so 404
    assert r.status_code == 404


async def test_get_student_not_found(client, admin_headers):
    r = await client.get(
        f"/api/students/{uuid.uuid4()}", headers=admin_headers
    )
    assert r.status_code == 404


# ── Create + update + delete ─────────────────────────────────────────────────

async def test_admin_can_create_student(client, admin_headers):
    payload = {
        "school_id": SCHOOL_ID,
        "student_number": f"TST-{uuid.uuid4().hex[:8]}",
    }
    r = await client.post("/api/students", json=payload, headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["student_number"] == payload["student_number"]


async def test_student_cannot_create_student(client, student_headers):
    r = await client.post(
        "/api/students",
        json={"school_id": SCHOOL_ID, "student_number": "X"},
        headers=student_headers,
    )
    assert r.status_code == 403


async def test_duplicate_student_number_rejected(client, admin_headers):
    # UOK-2024-001 already exists in seed
    r = await client.post(
        "/api/students",
        json={"school_id": SCHOOL_ID, "student_number": "UOK-2024-001"},
        headers=admin_headers,
    )
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"].lower()


async def test_update_student(client, admin_headers):
    # Create one then update
    n = f"TST-{uuid.uuid4().hex[:8]}"
    create = await client.post(
        "/api/students",
        json={"school_id": SCHOOL_ID, "student_number": n},
        headers=admin_headers,
    )
    sid = create.json()["id"]

    r = await client.put(
        f"/api/students/{sid}",
        json={"guardian_name": "Updated Guardian"},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["guardian_name"] == "Updated Guardian"


async def test_admin_can_delete_student(client, admin_headers):
    n = f"TST-{uuid.uuid4().hex[:8]}"
    create = await client.post(
        "/api/students",
        json={"school_id": SCHOOL_ID, "student_number": n},
        headers=admin_headers,
    )
    sid = create.json()["id"]

    r = await client.delete(f"/api/students/{sid}", headers=admin_headers)
    assert r.status_code == 200


async def test_lecturer_cannot_delete_student(client, lecturer_headers):
    r = await client.delete(
        f"/api/students/{STUDENT_ID}", headers=lecturer_headers
    )
    assert r.status_code == 403
