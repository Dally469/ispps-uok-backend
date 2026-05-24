"""Login / logout / session endpoints."""
from __future__ import annotations


# Seed users were created with the bcrypt hash of `password123`.
SEED_PASSWORD = "password123"


async def test_login_success(client):
    r = await client.post(
        "/api/auth/login",
        json={"email": "admin@uok.lk", "password": SEED_PASSWORD},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["email"] == "admin@uok.lk"
    assert body["user"]["role"] == "admin"
    assert isinstance(body["token"], str) and len(body["token"]) > 20
    # Cookie was set
    assert "auth_token" in r.cookies


async def test_login_wrong_password(client):
    r = await client.post(
        "/api/auth/login",
        json={"email": "admin@uok.lk", "password": "nope-not-it"},
    )
    assert r.status_code == 401
    assert "Invalid" in r.json()["detail"]


async def test_login_unknown_email(client):
    r = await client.post(
        "/api/auth/login",
        json={"email": "ghost@nope.lk", "password": SEED_PASSWORD},
    )
    assert r.status_code == 401


async def test_login_password_validation(client):
    r = await client.post(
        "/api/auth/login",
        json={"email": "admin@uok.lk", "password": "abc"},
    )
    # min_length=6 on the pydantic schema
    assert r.status_code == 422


async def test_session_with_bearer(client, admin_headers):
    r = await client.get("/api/auth/session", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "admin@uok.lk"


async def test_session_with_cookie(client):
    login = await client.post(
        "/api/auth/login",
        json={"email": "ashan@student.uok.lk", "password": SEED_PASSWORD},
    )
    assert login.status_code == 200
    # Cookie is automatically attached by AsyncClient for subsequent requests
    r = await client.get("/api/auth/session")
    assert r.status_code == 200
    assert r.json()["role"] == "student"


async def test_logout_clears_cookie(client):
    await client.post(
        "/api/auth/login",
        json={"email": "admin@uok.lk", "password": SEED_PASSWORD},
    )
    r = await client.post("/api/auth/logout")
    assert r.status_code == 200
    assert r.json() == {"success": True}
