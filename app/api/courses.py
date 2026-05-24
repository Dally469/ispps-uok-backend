from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models import Course, User, AcademicYear
from app.schemas import CourseCreate, CourseUpdate
from app.core.security import require_auth, require_role
from app.deps import auth_school_id, course_visibility_clause, resolve_school_scope

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("")
async def list_courses(
    request: Request,
    school_id: uuid.UUID | None = None,
    subject: str | None = None,
    lecturer_id: uuid.UUID | None = None,
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
            joinedload(Course.lecturer),
            joinedload(Course.academic_year),
        )
        .order_by(Course.name)
        .where(course_visibility_clause(auth))
    )

    if school_scope:
        q = q.where(Course.school_id == school_scope)
    if subject:
        q = q.where(Course.subject == subject)
    if lecturer_id:
        q = q.where(Course.lecturer_id == lecturer_id)
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
                Course.lecturer.has(User.full_name.ilike(term)),
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
        lecturer_id=body.lecturer_id,
        academic_year_id=body.academic_year_id,
        name=body.name,
        subject=body.subject,
        grade_level=body.grade_level,
        credit_hours=body.credit_hours,
    )
    db.add(course)
    await db.commit()
    # Re-fetch with relationships eagerly loaded. `db.refresh` only
    # reloads scalar columns, and lazy-loading relationships from an
    # async session raises MissingGreenlet.
    refreshed = await db.execute(
        select(Course)
        .options(joinedload(Course.lecturer), joinedload(Course.academic_year))
        .where(Course.id == course.id)
    )
    course = refreshed.unique().scalar_one()
    return _format_course(course)


@router.put("/{course_id}")
async def update_course(
    course_id: uuid.UUID,
    body: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin")),
):
    result = await db.execute(
        select(Course)
        .options(joinedload(Course.lecturer), joinedload(Course.academic_year))
        .where(Course.id == course_id)
    )
    course = result.unique().scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    school_id = auth_school_id(auth)
    if school_id and course.school_id != school_id:
        raise HTTPException(status_code=403, detail="Course is in another school")

    if body.lecturer_id is not None:
        lecturer_check = await db.execute(
            select(User).where(User.id == body.lecturer_id, User.role == "lecturer")
        )
        lecturer = lecturer_check.scalar_one_or_none()
        if not lecturer:
            raise HTTPException(status_code=422, detail="Selected user is not a lecturer")
        if school_id and lecturer.school_id != school_id:
            raise HTTPException(status_code=403, detail="Lecturer belongs to another school")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(course, field, value)

    await db.commit()
    refreshed = await db.execute(
        select(Course)
        .options(joinedload(Course.lecturer), joinedload(Course.academic_year))
        .where(Course.id == course.id)
    )
    return _format_course(refreshed.unique().scalar_one())


@router.delete("/{course_id}")
async def delete_course(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin")),
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    school_id = auth_school_id(auth)
    if school_id and course.school_id != school_id:
        raise HTTPException(status_code=403, detail="Course is in another school")

    await db.delete(course)
    await db.commit()
    return {"success": True}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _format_course(c: Course) -> dict:
    lecturer_data = None
    if c.lecturer:
        lecturer_data = {
            "id": str(c.lecturer.id),
            "full_name": c.lecturer.full_name,
            "email": c.lecturer.email,
            "avatar_url": c.lecturer.avatar_url,
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
        "lecturer_id": str(c.lecturer_id) if c.lecturer_id else None,
        "academic_year_id": str(c.academic_year_id),
        "name": c.name,
        "subject": c.subject,
        "grade_level": c.grade_level,
        "credit_hours": c.credit_hours,
        "lecturer": lecturer_data,
        "academic_year": ay_data,
    }
