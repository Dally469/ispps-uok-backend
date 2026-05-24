from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import get_db
from app.models import Attendance, Enrollment, Student, User, Course
from app.schemas import AttendanceCreate, BulkAttendanceRequest
from app.core.security import require_auth, require_role
from app.deps import attendance_visibility_clause, auth_user_id, resolve_school_scope

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


@router.get("")
async def list_attendance(
    request: Request,
    enrollment_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
    course_id: uuid.UUID | None = None,
    school_id: uuid.UUID | None = None,
    status: str | None = None,
    recorded_by: uuid.UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    school_scope = resolve_school_scope(auth, school_id)
    q = (
        select(Attendance)
        .options(
            joinedload(Attendance.enrollment)
            .joinedload(Enrollment.student)
            .joinedload(Student.user),
            joinedload(Attendance.enrollment)
            .joinedload(Enrollment.course),
        )
        .order_by(Attendance.date.desc())
        .where(attendance_visibility_clause(auth))
    )

    if school_scope:
        q = q.where(
            Attendance.enrollment.has(
                Enrollment.student.has(Student.school_id == school_scope)
            )
        )
    if enrollment_id:
        q = q.where(Attendance.enrollment_id == enrollment_id)
    if student_id:
        q = q.where(Attendance.enrollment.has(Enrollment.student_id == student_id))
    if course_id:
        q = q.where(Attendance.enrollment.has(Enrollment.course_id == course_id))
    if status:
        q = q.where(Attendance.status == status)
    if recorded_by:
        q = q.where(Attendance.recorded_by == recorded_by)
    if date_from:
        q = q.where(Attendance.date >= date_from)
    if date_to:
        q = q.where(Attendance.date <= date_to)
    q = q.offset(offset).limit(limit)

    result = await db.execute(q)
    records = result.unique().scalars().all()

    return [_format_attendance(r) for r in records]


@router.post("")
async def create_attendance(
    body: AttendanceCreate,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "lecturer")),
):
    enrollment_result = await db.execute(
        select(Enrollment)
        .options(joinedload(Enrollment.course), joinedload(Enrollment.student))
        .where(Enrollment.id == body.enrollment_id)
    )
    enrollment = enrollment_result.unique().scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    if auth.get("role") == "lecturer":
        if not enrollment.course or enrollment.course.lecturer_id != auth_user_id(auth):
            raise HTTPException(status_code=403, detail="You can only manage attendance for your courses")

    record = Attendance(
        enrollment_id=body.enrollment_id,
        date=body.date,
        status=body.status,
        note=body.note,
        recorded_by=auth["userId"],
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return _simple_attendance(record)


@router.post("/bulk")
async def bulk_attendance(
    body: BulkAttendanceRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "lecturer")),
):
    # Verify enrollments belong to the course
    result = await db.execute(select(Course).where(Course.id == body.course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if auth.get("role") == "lecturer" and course.lecturer_id != auth_user_id(auth):
        raise HTTPException(status_code=403, detail="You can only manage attendance for your courses")

    result = await db.execute(select(Enrollment.id).where(Enrollment.course_id == body.course_id))
    valid_ids = {row[0] for row in result.all()}

    insert_data = []
    for r in body.records:
        if r.enrollment_id in valid_ids:
            insert_data.append({
                "enrollment_id": r.enrollment_id,
                "date": body.date,
                "status": r.status,
                "note": r.note,
                "recorded_by": uuid.UUID(auth["userId"]),
            })

    if not insert_data:
        raise HTTPException(status_code=400, detail="No valid enrollment records")

    # Upsert (on conflict enrollment_id + date)
    stmt = pg_insert(Attendance).values(insert_data)
    stmt = stmt.on_conflict_do_update(
        constraint="attendance_enrollment_id_date_key",
        set_={"status": stmt.excluded.status, "note": stmt.excluded.note, "recorded_by": stmt.excluded.recorded_by},
    )
    await db.execute(stmt)
    await db.commit()

    return {"inserted": len(insert_data), "records": insert_data}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _simple_attendance(a: Attendance) -> dict:
    return {
        "id": str(a.id),
        "enrollment_id": str(a.enrollment_id),
        "date": str(a.date),
        "status": a.status,
        "note": a.note,
        "recorded_by": str(a.recorded_by) if a.recorded_by else None,
    }


def _format_attendance(a: Attendance) -> dict:
    enrollment = a.enrollment
    student_data = None
    course_data = None

    if enrollment:
        if enrollment.student:
            s = enrollment.student
            student_data = {
                "id": str(s.id),
                "student_number": s.student_number,
                "user": {"full_name": s.user.full_name} if s.user else None,
            }
        if enrollment.course:
            c = enrollment.course
            course_data = {"id": str(c.id), "name": c.name, "subject": c.subject}

    return {
        "id": str(a.id),
        "enrollment_id": str(a.enrollment_id),
        "date": str(a.date),
        "status": a.status,
        "note": a.note,
        "recorded_by": str(a.recorded_by) if a.recorded_by else None,
        "enrollment": {
            "id": str(enrollment.id) if enrollment else None,
            "student": student_data,
            "course": course_data,
        } if enrollment else None,
    }
