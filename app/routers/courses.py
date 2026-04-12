from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models import Course, User, AcademicYear
from app.schemas import CourseCreate
from app.utils.auth import require_auth, require_role
from app.utils.access import course_visibility_clause, resolve_school_scope

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("")
async def list_courses(
    request: Request,
    school_id: uuid.UUID | None = None,
    subject: str | None = None,
    teacher_id: uuid.UUID | None = None,
    academic_year_id: uuid.UUID | None = None,
    grade_level: str | None = None,
    is_active_year: bool | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    school_scope = resolve_school_scope(auth, school_id)
    q = (
        select(Course)
        .options(
            joinedload(Course.teacher),
            joinedload(Course.academic_year),
        )
        .order_by(Course.name)
        .where(course_visibility_clause(auth))
    )

    if school_scope:
        q = q.where(Course.school_id == school_scope)
    if subject:
        q = q.where(Course.subject == subject)
    if teacher_id:
        q = q.where(Course.teacher_id == teacher_id)
    if academic_year_id:
        q = q.where(Course.academic_year_id == academic_year_id)
    if grade_level:
        q = q.where(Course.grade_level == grade_level)
    if is_active_year is not None:
        q = q.where(Course.academic_year.has(AcademicYear.is_active == is_active_year))
    if search:
        term = f"%{search}%"
        q = q.where(
            or_(
                Course.name.ilike(term),
                Course.subject.ilike(term),
                Course.grade_level.ilike(term),
                Course.teacher.has(User.full_name.ilike(term)),
            )
        )

    q = q.offset(offset).limit(limit)

    result = await db.execute(q)
    courses = result.unique().scalars().all()

    return [_format_course(c) for c in courses]


@router.post("")
async def create_course(
    body: CourseCreate,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin")),
):
    course = Course(
        school_id=body.school_id,
        teacher_id=body.teacher_id,
        academic_year_id=body.academic_year_id,
        name=body.name,
        subject=body.subject,
        grade_level=body.grade_level,
        credit_hours=body.credit_hours,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course, attribute_names=["teacher"])

    return _format_course(course)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _format_course(c: Course) -> dict:
    teacher_data = None
    if c.teacher:
        teacher_data = {
            "id": str(c.teacher.id),
            "full_name": c.teacher.full_name,
            "email": c.teacher.email,
            "avatar_url": c.teacher.avatar_url,
        }

    ay_data = None
    if c.academic_year:
        ay_data = {
            "id": str(c.academic_year.id),
            "label": c.academic_year.label,
            "is_active": c.academic_year.is_active,
        }

    return {
        "id": str(c.id),
        "school_id": str(c.school_id),
        "teacher_id": str(c.teacher_id) if c.teacher_id else None,
        "academic_year_id": str(c.academic_year_id),
        "name": c.name,
        "subject": c.subject,
        "grade_level": c.grade_level,
        "credit_hours": c.credit_hours,
        "teacher": teacher_data,
        "academic_year": ay_data,
    }
