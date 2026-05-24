"""Shared fixtures for the backend test suite.

The suite uses a dedicated `ispps_test` PostgreSQL database which is
dropped, recreated, and seeded once per pytest session. Tests are
read-mostly; the few that mutate use unique values so concurrent runs
do not collide.

Env overrides (DATABASE_URL, JWT_SECRET) MUST be applied before
`app.main` is imported because `app.core.database` builds the SQLAlchemy
engine at import time from the resolved settings.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

# ── Env overrides (must come before any `from app ...` import) ───────────────
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEST_DB_NAME = "ispps_test"
TEST_DB_URL = f"postgresql+asyncpg://postgres:123@localhost:5432/{TEST_DB_NAME}"
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["JWT_SECRET"] = "test-secret-do-not-use-in-prod-0000000000"

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402

# Invalidate any cached settings instance picked up before env overrides.
get_settings.cache_clear()

# Importing app.main also creates the async engine - it now points at the
# test DB because the env was set above.
from app.main import app  # noqa: E402
from app.core.security import sign_token  # noqa: E402

# ── Engine override for tests ────────────────────────────────────────────────
# The default engine uses a connection pool, which on Windows + asyncpg
# binds connections to the event loop they were created on. pytest creates
# fresh loops between tests, so pooled connections become unusable. We
# replace the engine + session maker with a NullPool variant so every
# request opens a fresh connection on the current loop.
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

import app.core.database as _db_module  # noqa: E402

_test_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool, echo=False)
_db_module.engine = _test_engine
_db_module.async_session = async_sessionmaker(
    _test_engine, class_=AsyncSession, expire_on_commit=False
)


SCHEMA_FILE = ROOT / "db" / "schema.sql"
SEED_FILE = ROOT / "db" / "seed.sql"


# ── Seed-data constants (referenced across many tests) ───────────────────────
SCHOOL_ID = "a0000000-0000-0000-0000-000000000001"
ACADEMIC_YEAR_ID = "b0000000-0000-0000-0000-000000000001"
ADMIN_USER_ID = "c0000000-0000-0000-0000-000000000001"
LECTURER_USER_ID = "c0000000-0000-0000-0000-000000000002"  # Dr. Silva (DSA + Calculus)
OTHER_LECTURER_USER_ID = "c0000000-0000-0000-0000-000000000003"  # Dr. Perera (DBMS + Physics)
STUDENT_USER_ID = "d0000000-0000-0000-0000-000000000001"  # Ashan
STUDENT_ID = "f0000000-0000-0000-0000-000000000001"
OTHER_STUDENT_ID = "f0000000-0000-0000-0000-000000000002"
DSA_COURSE_ID = "aa000000-0000-0000-0000-000000000001"
DBMS_COURSE_ID = "aa000000-0000-0000-0000-000000000002"
ENROLLMENT_ID = "bb000000-0000-0000-0000-000000000001"  # Ashan in DSA


def _psql(*args: str, db: str = "postgres", check: bool = True) -> subprocess.CompletedProcess:
    env = {**os.environ, "PGPASSWORD": "123"}
    cmd = ["psql", "-h", "localhost", "-U", "postgres", "-d", db, *args]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"psql failed (exit {result.returncode}): {' '.join(cmd)}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


@pytest.fixture(scope="session")
def event_loop():
    """Override pytest-asyncio's default to use one loop per session.

    Without this, the session-scoped async fixtures bind to a loop that
    function-scoped tests don't reuse, causing 'attached to a different
    loop' errors on the SQLAlchemy async engine.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Drop, recreate, and seed the test DB once per session."""
    _psql("-c", f"drop database if exists {TEST_DB_NAME}", db="postgres")
    _psql("-c", f"create database {TEST_DB_NAME}", db="postgres")
    _psql("-v", "ON_ERROR_STOP=1", "-f", str(SCHEMA_FILE), db=TEST_DB_NAME)
    _psql("-v", "ON_ERROR_STOP=1", "-f", str(SEED_FILE), db=TEST_DB_NAME)
    yield


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── Auth helpers ─────────────────────────────────────────────────────────────

def _token(user_id: str, role: str, email: str, school_id: str | None = SCHOOL_ID) -> str:
    return sign_token(
        {"userId": user_id, "email": email, "role": role, "schoolId": school_id}
    )


@pytest.fixture
def admin_token() -> str:
    return _token(ADMIN_USER_ID, "admin", "admin@uok.lk")


@pytest.fixture
def lecturer_token() -> str:
    return _token(LECTURER_USER_ID, "lecturer", "drsilva@uok.lk")


@pytest.fixture
def other_lecturer_token() -> str:
    return _token(OTHER_LECTURER_USER_ID, "lecturer", "drperera@uok.lk")


@pytest.fixture
def student_token() -> str:
    return _token(STUDENT_USER_ID, "student", "ashan@student.uok.lk")


@pytest.fixture
def admin_headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def lecturer_headers(lecturer_token) -> dict:
    return {"Authorization": f"Bearer {lecturer_token}"}


@pytest.fixture
def other_lecturer_headers(other_lecturer_token) -> dict:
    return {"Authorization": f"Bearer {other_lecturer_token}"}


@pytest.fixture
def student_headers(student_token) -> dict:
    return {"Authorization": f"Bearer {student_token}"}
