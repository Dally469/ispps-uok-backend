"""Smoke + JWT/RBAC primitives."""
from __future__ import annotations

import pytest
from jose import jwt

from app.core.config import get_settings
from app.core.security import hash_password, sign_token, verify_password


async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_jwt_roundtrip():
    token = sign_token({"userId": "u1", "role": "admin", "schoolId": None})
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert payload["userId"] == "u1"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_password_hash_verify():
    h = hash_password("secret123")
    assert h != "secret123"
    assert verify_password("secret123", h)
    assert not verify_password("wrong", h)


async def test_protected_endpoint_requires_token(client):
    r = await client.get("/api/students")
    assert r.status_code == 401


async def test_invalid_token_rejected(client):
    r = await client.get("/api/students", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


async def test_admin_only_endpoint_blocks_student(client, student_headers):
    r = await client.get("/api/admin/users", headers=student_headers)
    assert r.status_code == 403


async def test_admin_only_endpoint_blocks_lecturer(client, lecturer_headers):
    r = await client.get("/api/admin/users", headers=lecturer_headers)
    assert r.status_code == 403
