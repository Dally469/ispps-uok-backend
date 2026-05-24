from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.security import require_role
from app.deps import auth_school_id, auth_user_id
from app.models import Course, Enrollment, Student, User
from app.schemas import BulkEnrollRequest, EnrollmentCreate, EnrollmentUpdate


router = APIRouter(prefix="/api/enrollments", tags=["enrollments"])


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _assert_can_modify_course(db: AsyncSession, auth: dict, course_id: uuid.UUID) -> Course:
    """Lecturers may only manage their own courses; admins anything in their school."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    school_id = auth_school_id(auth)
    if school_id and course.school_id != school_id:
        raise HTTPException(status_code=403, detail="Course is in another school")

    if auth.get("role") == "lecturer" and course.lecturer_id != auth_user_id(auth):
        raise HTTPException(
            status_code=403,
            detail="You can only manage enrollments for courses you teach",
        )
    return course


async def _assert_can_see_student(db: AsyncSession, auth: dict, student_id: uuid.UUID) -> Student:
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    school_id = auth_school_id(auth)
    if school_id and student.school_id != school_id:
        raise HTTPException(status_code=403, detail="Student is in another school")
    return student


def _format(e: Enrollment) -> dict:
    return {
        "id": str(e.id),
        "student_id": str(e.student_id),
        "course_id": str(e.course_id),
        "status": e.status,
        "enrolled_at": e.enrolled_at.isoformat() if e.enrolled_at else None,
        "course": {
            "id": str(e.course.id),
            "name": e.course.name,
            "subject": e.course.subject,
            "credit_hours": e.course.credit_hours,
        } if e.course else None,
        "student": {
            "id": str(e.student.id),
            "student_number": e.student.student_number,
            "full_name": e.student.user.full_name if e.student and e.student.user else None,
        } if e.student else None,
    }


# ── List ─────────────────────────────────────────────────────────────────────

@router.get("")
async def list_enrollments(
    student_id: uuid.UUID | None = None,
    course_id: uuid.UUID | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "lecturer", "student")),
):
    q = (
        select(Enrollment)
        .options(
            joinedload(Enrollment.course),
            joinedload(Enrollment.student).joinedload(Student.user),
        )
        .order_by(Enrollment.enrolled_at.desc())
    )
    if student_id:
        q = q.where(Enrollment.student_id == student_id)
    if course_id:
        q = q.where(Enrollment.course_id == course_id)
    if status:
        q = q.where(Enrollment.status == status)

    role = auth.get("role")
    if role == "lecturer":
        q = q.where(Enrollment.course.has(Course.lecturer_id == auth_user_id(auth)))
    elif role == "student":
        q = q.where(Enrollment.student.has(Student.user_id == auth_user_id(auth)))

    school_id = auth_school_id(auth)
    if school_id:
        q = q.where(Enrollment.student.has(Student.school_id == school_id))

    result = await db.execute(q)
    return [_format(e) for e in result.unique().scalars().all()]


# ── Create one ───────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_enrollment(
    body: EnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "lecturer")),
):
    await _assert_can_modify_course(db, auth, body.course_id)
    await _assert_can_see_student(db, auth, body.student_id)

    enrollment = Enrollment(
        student_id=body.student_id,
        course_id=body.course_id,
        status=body.status,
    )
    db.add(enrollment)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Student is already enrolled in this course")
    await db.refresh(enrollment, attribute_names=["course", "student"])
    if enrollment.student:
        await db.refresh(enrollment.student, attribute_names=["user"])
    return _format(enrollment)


# ── Bulk enroll into a course ────────────────────────────────────────────────

@router.post("/bulk", status_code=201)
async def bulk_enroll(
    body: BulkEnrollRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "lecturer")),
):
    await _assert_can_modify_course(db, auth, body.course_id)

    school_id = auth_school_id(auth)
    if school_id:
        check = await db.execute(
            select(Student.id).where(
                Student.id.in_(body.student_ids),
                Student.school_id == school_id,
            )
        )
        valid = {row[0] for row in check.all()}
        invalid = set(body.student_ids) - valid
        if invalid:
            raise HTTPException(
                status_code=403,
                detail=f"{len(invalid)} student(s) are outside your school",
            )

    existing = await db.execute(
        select(Enrollment.student_id).where(
            Enrollment.course_id == body.course_id,
            Enrollment.student_id.in_(body.student_ids),
        )
    )
    already = {row[0] for row in existing.all()}

    new_ids = [sid for sid in body.student_ids if sid not in already]
    for sid in new_ids:
        db.add(Enrollment(student_id=sid, course_id=body.course_id, status="active"))

    await db.commit()
    return {
        "enrolled": len(new_ids),
        "skipped_existing": len(already),
    }


# ── Update status ────────────────────────────────────────────────────────────

@router.put("/{enrollment_id}")
async def update_enrollment(
    enrollment_id: uuid.UUID,
    body: EnrollmentUpdate,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "lecturer")),
):
    result = await db.execute(
        select(Enrollment)
        .options(
            joinedload(Enrollment.course),
            joinedload(Enrollment.student).joinedload(Student.user),
        )
        .where(Enrollment.id == enrollment_id)
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    await _assert_can_modify_course(db, auth, enrollment.course_id)

    enrollment.status = body.status
    await db.commit()
    return _format(enrollment)


# ── Delete ───────────────────────────────────────────────────────────────────

@router.delete("/{enrollment_id}")
async def delete_enrollment(
    enrollment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "lecturer")),
):
    result = await db.execute(select(Enrollment).where(Enrollment.id == enrollment_id))
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    await _assert_can_modify_course(db, auth, enrollment.course_id)
    await db.delete(enrollment)
    await db.commit()
    return {"success": True}
