from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


# ── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserUpdate(BaseModel):
    """Admin-only partial update of a user account.

    `role` is intentionally NOT editable — changing it would leave any
    linked Student row inconsistent. Delete + recreate the account if
    the role really needs to change.
    """
    full_name: str | None = Field(default=None, min_length=2)
    email: EmailStr | None = None
    school_id: uuid.UUID | None = None
    password: str | None = Field(default=None, min_length=6)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=8)
    new_password: str = Field(min_length=6)


class UserCreate(BaseModel):
    """Admin-only: create a new user account.

    If `role == "student"`, a linked Student record is created at the same
    time using `student_number`, `date_of_birth`, `gender`, and the guardian
    fields. Those fields are ignored for other roles.
    """
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=2)
    role: Literal["admin", "lecturer", "student"]
    school_id: uuid.UUID | None = None

    # Required only when role == "student"
    student_number: str | None = None
    date_of_birth: date | None = None
    gender: Literal["male", "female", "other"] | None = None
    guardian_name: str | None = None
    guardian_email: EmailStr | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    avatar_url: str | None = None
    school_id: uuid.UUID | None = None
    school_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    token: str
    user: UserOut


# ── Students ─────────────────────────────────────────────────────────────────

class StudentCreate(BaseModel):
    user_id: uuid.UUID | None = None
    school_id: uuid.UUID
    student_number: str = Field(min_length=1)
    date_of_birth: date | None = None
    gender: Literal["male", "female", "other"] | None = None
    guardian_name: str | None = None
    guardian_email: str | None = None


class StudentUpdate(BaseModel):
    student_number: str | None = None
    date_of_birth: date | None = None
    gender: Literal["male", "female", "other"] | None = None
    guardian_name: str | None = None
    guardian_email: str | None = None


# ── Attendance ───────────────────────────────────────────────────────────────

class AttendanceCreate(BaseModel):
    enrollment_id: uuid.UUID
    date: date
    status: Literal["present", "absent", "late", "excused"]
    note: str | None = None


class BulkAttendanceRecord(BaseModel):
    enrollment_id: uuid.UUID
    status: Literal["present", "absent", "late", "excused"]
    note: str | None = None


class BulkAttendanceRequest(BaseModel):
    course_id: uuid.UUID
    date: date
    records: list[BulkAttendanceRecord]


# ── Grades ───────────────────────────────────────────────────────────────────

class GradeCreate(BaseModel):
    enrollment_id: uuid.UUID
    assessment_type: Literal["quiz", "midterm", "final", "assignment", "project", "lab"]
    title: str = Field(min_length=1)
    score: float = Field(ge=0)
    max_score: float = Field(ge=1)
    weight: float = Field(ge=0, le=1, default=1.0)
    assessed_on: date | None = None


class GradeUpdate(BaseModel):
    """Partial update — only fields explicitly set are applied."""
    assessment_type: Literal["quiz", "midterm", "final", "assignment", "project", "lab"] | None = None
    title: str | None = Field(default=None, min_length=1)
    score: float | None = Field(default=None, ge=0)
    max_score: float | None = Field(default=None, ge=1)
    weight: float | None = Field(default=None, ge=0, le=1)
    assessed_on: date | None = None


class BulkGradeRow(BaseModel):
    enrollment_id: uuid.UUID
    score: float = Field(ge=0)


class BulkGradeRequest(BaseModel):
    """Record one assessment for many students in a single course."""
    course_id: uuid.UUID
    assessment_type: Literal["quiz", "midterm", "final", "assignment", "project", "lab"]
    title: str = Field(min_length=1)
    max_score: float = Field(ge=1)
    weight: float = Field(ge=0, le=1, default=0.1)
    assessed_on: date | None = None
    rows: list[BulkGradeRow] = Field(min_length=1)


# ── Courses ──────────────────────────────────────────────────────────────────

class CourseCreate(BaseModel):
    school_id: uuid.UUID
    lecturer_id: uuid.UUID | None = None
    academic_year_id: uuid.UUID
    name: str
    subject: str
    grade_level: str | None = None
    credit_hours: int = 3


class CourseUpdate(BaseModel):
    """Partial update — only fields explicitly set are applied."""
    lecturer_id: uuid.UUID | None = None
    academic_year_id: uuid.UUID | None = None
    name: str | None = None
    subject: str | None = None
    grade_level: str | None = None
    credit_hours: int | None = None


# ── Enrollments ──────────────────────────────────────────────────────────────

class EnrollmentCreate(BaseModel):
    student_id: uuid.UUID
    course_id: uuid.UUID
    status: Literal["active", "dropped", "completed"] = "active"


class EnrollmentUpdate(BaseModel):
    status: Literal["active", "dropped", "completed"]


class BulkEnrollRequest(BaseModel):
    course_id: uuid.UUID
    student_ids: list[uuid.UUID] = Field(min_length=1)


# ── Predictions ──────────────────────────────────────────────────────────────

class PredictionCreate(BaseModel):
    student_id: uuid.UUID
    course_id: uuid.UUID | None = None
    predicted_grade: float
    pass_probability: float
    risk_level: Literal["low", "medium", "high", "critical"]
    factors: list[dict] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    ai_summary: str | None = None


class PredictRequest(BaseModel):
    student_id: uuid.UUID
    course_id: uuid.UUID | None = None


class InsightsRequest(BaseModel):
    student_id: uuid.UUID


class RecommendRequest(BaseModel):
    student_id: uuid.UUID


# ── Import ───────────────────────────────────────────────────────────────────

class CSVImportRequest(BaseModel):
    csv_data: str
