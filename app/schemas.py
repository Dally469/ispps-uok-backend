from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


# ── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = Field(min_length=2)
    role: Literal["admin", "teacher", "student", "parent"]
    school_id: uuid.UUID | None = None


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    avatar_url: str | None = None
    school_id: uuid.UUID | None = None
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


# ── Courses ──────────────────────────────────────────────────────────────────

class CourseCreate(BaseModel):
    school_id: uuid.UUID
    teacher_id: uuid.UUID | None = None
    academic_year_id: uuid.UUID
    name: str
    subject: str
    grade_level: str | None = None
    credit_hours: int = 3


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


class ChatRequest(BaseModel):
    message: str
    student_id: uuid.UUID | None = None
    history: list[dict] | None = None


# ── Import ───────────────────────────────────────────────────────────────────

class CSVImportRequest(BaseModel):
    csv_data: str
