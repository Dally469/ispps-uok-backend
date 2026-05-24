"""Courses router."""
from __future__ import annotations

import uuid

from tests.conftest import (
    ACADEMIC_YEAR_ID,
    LECTURER_USER_ID,
    SCHOOL_ID,
)


async def test_admin_lists_all_courses(client, admin_headers):
    r = await client.get("/api/courses", headers=admin_headers)
    assert r.status_code == 200, r.text
    courses = r.json()
    # 5 courses in seed
    assert len(courses) == 5
    names = {c["name"] for c in courses}
    assert "Data Structures & Algorithms" in names


async def test_lecturer_only_sees_own_courses(client, lecturer_headers):
    r = await client.get("/api/courses", headers=lecturer_headers)
    assert r.status_code == 200
    courses = r.json()
    # Dr. Silva teaches DSA + Calculus II
    for c in courses:
        assert c["lecturer_id"] == LECTURER_USER_ID


async def test_student_sees_enrolled_courses_only(client, student_headers):
    r = await client.get("/api/courses", headers=student_headers)
    assert r.status_code == 200
    # Ashan is enrolled in DSA + DBMS
    assert len(r.json()) >= 1


async def test_courses_search_by_subject(client, admin_headers):
    r = await client.get("/api/courses?subject=Computer Science", headers=admin_headers)
    assert r.status_code == 200
    for c in r.json():
        assert c["subject"] == "Computer Science"


async def test_courses_search_by_term(client, admin_headers):
    r = await client.get("/api/courses?search=Calculus", headers=admin_headers)
    assert r.status_code == 200
    assert any("Calculus" in c["name"] for c in r.json())


async def test_admin_can_create_course(client, admin_headers):
    payload = {
        "school_id": SCHOOL_ID,
        "academic_year_id": ACADEMIC_YEAR_ID,
        "lecturer_id": LECTURER_USER_ID,
        "name": f"Test Course {uuid.uuid4().hex[:6]}",
        "subject": "Computer Science",
        "credit_hours": 4,
    }
    r = await client.post("/api/courses", json=payload, headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == payload["name"]
    assert body["credit_hours"] == 4


async def test_lecturer_cannot_create_course(client, lecturer_headers):
    r = await client.post(
        "/api/courses",
        json={
            "school_id": SCHOOL_ID,
            "academic_year_id": ACADEMIC_YEAR_ID,
            "name": "Sneaky",
            "subject": "X",
        },
        headers=lecturer_headers,
    )
    assert r.status_code == 403


async def test_student_cannot_create_course(client, student_headers):
    r = await client.post(
        "/api/courses",
        json={
            "school_id": SCHOOL_ID,
            "academic_year_id": ACADEMIC_YEAR_ID,
            "name": "Sneakier",
            "subject": "X",
        },
        headers=student_headers,
    )
    assert r.status_code == 403
