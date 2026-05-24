"""Admin + reports + imports routers."""
from __future__ import annotations

import uuid

from tests.conftest import SCHOOL_ID, STUDENT_ID


# ── Admin users list ─────────────────────────────────────────────────────────

async def test_admin_lists_users(client, admin_headers):
    r = await client.get("/api/admin/users", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    # 16 users in seed
    assert len(body) >= 16
    assert any(u["role"] == "admin" for u in body)


async def test_admin_filter_by_role(client, admin_headers):
    r = await client.get("/api/admin/users?role=lecturer", headers=admin_headers)
    assert r.status_code == 200
    for u in r.json():
        assert u["role"] == "lecturer"


async def test_admin_user_search(client, admin_headers):
    r = await client.get("/api/admin/users?search=silva", headers=admin_headers)
    assert r.status_code == 200
    assert any("Silva" in u["full_name"] for u in r.json())


# ── Reports / export ─────────────────────────────────────────────────────────

async def test_export_csv(client, admin_headers):
    r = await client.get(
        f"/api/reports/export?school_id={SCHOOL_ID}&format=csv",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    text = r.text
    assert "Student Number" in text
    assert "UOK-2024-001" in text  # at least one student row


async def test_export_json(client, admin_headers):
    r = await client.get(
        f"/api/reports/export?school_id={SCHOOL_ID}&format=json",
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert body
    assert "enrollments" in body[0]


async def test_export_single_student(client, admin_headers):
    r = await client.get(
        f"/api/reports/export?school_id={SCHOOL_ID}&format=json&student_id={STUDENT_ID}",
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["student_number"] == "UOK-2024-001"


async def test_student_export_only_self(client, student_headers):
    r = await client.get(
        f"/api/reports/export?school_id={SCHOOL_ID}&format=json",
        headers=student_headers,
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


# ── CSV imports ──────────────────────────────────────────────────────────────

async def test_admin_import_students(client, admin_headers):
    unique = uuid.uuid4().hex[:6]
    csv_data = (
        "student_number,full_name,email,school_id\n"
        f"IMP-{unique}-A,Imported Alice,alice.{unique}@imp.lk,{SCHOOL_ID}\n"
        f"IMP-{unique}-B,Imported Bob,bob.{unique}@imp.lk,{SCHOOL_ID}\n"
    )
    r = await client.post(
        "/api/import/students",
        json={"csv_data": csv_data},
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["imported"] == 2
    assert body["errors"] == []


async def test_import_rejects_missing_fields(client, admin_headers):
    csv_data = (
        "student_number,full_name,email,school_id\n"
        ",Missing Number,nope@x.com,\n"
    )
    r = await client.post(
        "/api/import/students",
        json={"csv_data": csv_data},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["imported"] == 0
    assert r.json()["errors"]


async def test_import_requires_admin(client, lecturer_headers):
    r = await client.post(
        "/api/import/students",
        json={"csv_data": "student_number,full_name,school_id\nX,Y,Z\n"},
        headers=lecturer_headers,
    )
    assert r.status_code == 403


async def test_import_rejects_empty_csv(client, admin_headers):
    r = await client.post(
        "/api/import/students",
        json={"csv_data": "header_only_no_rows"},
        headers=admin_headers,
    )
    assert r.status_code == 400
