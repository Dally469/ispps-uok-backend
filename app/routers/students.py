from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.database import get_db
from app.models import (
    Student, User, Enrollment, Course, Grade, Attendance, Prediction, AiInsight,
)
from app.schemas import StudentCreate, StudentUpdate
from app.utils.auth import require_auth, require_role
from app.utils.access import filter_enrollments_for_role, resolve_school_scope, student_visibility_clause

router = APIRouter(prefix="/api/students", tags=["students"])


def _student_user_fields(user: User | None) -> dict | None:
    if not user:
        return None
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": user.avatar_url,
    }


@router.get("")
async def list_students(
    request: Request,
    search: str | None = None,
    gender: str | None = None,
    course_id: uuid.UUID | None = None,
    risk_level: str | None = None,
    has_predictions: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    q = (
        select(Student)
        .options(joinedload(Student.user))
        .order_by(Student.enrolled_at.desc())
        .where(student_visibility_clause(auth))
    )

    if search:
        term = f"%{search}%"
        q = q.where(
            or_(
                Student.student_number.ilike(term),
                Student.guardian_name.ilike(term),
                Student.guardian_email.ilike(term),
                Student.user.has(or_(User.full_name.ilike(term), User.email.ilike(term))),
            )
        )
    if gender:
        q = q.where(Student.gender == gender)
    if course_id:
        q = q.where(Student.enrollments.any(Enrollment.course_id == course_id))
    if risk_level:
        q = q.where(Student.predictions.any(Prediction.risk_level == risk_level))
    if has_predictions is True:
        q = q.where(Student.predictions.any())
    elif has_predictions is False:
        q = q.where(~Student.predictions.any())

    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    students = result.unique().scalars().all()

    return [
        {
            **_student_to_dict(s),
            "user": _student_user_fields(s.user),
        }
        for s in students
    ]


@router.post("")
async def create_student(
    body: StudentCreate,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "teacher")),
):
    resolve_school_scope(auth, body.school_id)
    student = Student(
        school_id=body.school_id,
        student_number=body.student_number,
        user_id=body.user_id,
        date_of_birth=body.date_of_birth,
        gender=body.gender,
        guardian_name=body.guardian_name,
        guardian_email=body.guardian_email,
    )
    db.add(student)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        detail = "Unable to create student"
        message = str(getattr(exc, "orig", exc)).lower()
        if "students_student_number_key" in message or "student_number" in message:
            detail = "Student number already exists"
        elif "students_user_id_key" in message or "user_id" in message:
            detail = "Student user is already linked"
        raise HTTPException(status_code=409, detail=detail)
    await db.refresh(student, attribute_names=["user"])

    return {
        **_student_to_dict(student),
        "user": _student_user_fields(student.user),
    }


@router.get("/{student_id}")
async def get_student(
    student_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    result = await db.execute(
        select(Student)
        .options(
            joinedload(Student.user),
            selectinload(Student.enrollments)
            .joinedload(Enrollment.course)
            .joinedload(Course.teacher),
            selectinload(Student.enrollments)
            .selectinload(Enrollment.grades),
            selectinload(Student.enrollments)
            .selectinload(Enrollment.attendance_records),
        )
        .where(Student.id == student_id, student_visibility_clause(auth))
    )
    student = result.unique().scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    visible_enrollments = filter_enrollments_for_role(student.enrollments, auth)
    visible_course_ids = {enrollment.course_id for enrollment in visible_enrollments}

    # Fetch predictions
    pred_result = await db.execute(
        select(Prediction)
        .where(Prediction.student_id == student_id)
        .order_by(Prediction.generated_at.desc())
        .limit(10)
    )
    predictions = pred_result.scalars().all()
    if auth.get("role") == "teacher":
        predictions = [
            prediction
            for prediction in predictions
            if prediction.course_id is None or prediction.course_id in visible_course_ids
        ]

    # Fetch AI insights
    insight_result = await db.execute(
        select(AiInsight)
        .where(AiInsight.student_id == student_id)
        .order_by(AiInsight.created_at.desc())
        .limit(10)
    )
    insights = insight_result.scalars().all()

    user_data = None
    if student.user:
        user_data = {
            "id": str(student.user.id),
            "email": student.user.email,
            "full_name": student.user.full_name,
            "avatar_url": student.user.avatar_url,
            "role": student.user.role,
        }

    enrollments_out = []
    for e in visible_enrollments:
        teacher_data = None
        if e.course and e.course.teacher:
            teacher_data = {
                "id": str(e.course.teacher.id),
                "full_name": e.course.teacher.full_name,
                "email": e.course.teacher.email,
            }

        course_data = None
        if e.course:
            course_data = {
                **_course_to_dict(e.course),
                "teacher": teacher_data,
            }

        enrollments_out.append({
            "id": str(e.id),
            "student_id": str(e.student_id),
            "course_id": str(e.course_id),
            "enrolled_at": e.enrolled_at.isoformat() if e.enrolled_at else None,
            "status": e.status,
            "course": course_data,
            "grades": [_grade_to_dict(g) for g in e.grades],
            "attendance": [_attendance_to_dict(a) for a in e.attendance_records],
        })

    return {
        **_student_to_dict(student),
        "user": user_data,
        "enrollments": enrollments_out,
        "predictions": [_prediction_to_dict(p) for p in predictions],
        "insights": [_insight_to_dict(i) for i in insights],
    }


@router.put("/{student_id}")
async def update_student(
    student_id: uuid.UUID,
    body: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "teacher")),
):
    result = await db.execute(
        select(Student)
        .options(joinedload(Student.user))
        .where(Student.id == student_id, student_visibility_clause(auth))
    )
    student = result.unique().scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(student, key, value)

    await db.commit()
    await db.refresh(student, attribute_names=["user"])

    return {
        **_student_to_dict(student),
        "user": _student_user_fields(student.user),
    }


@router.delete("/{student_id}")
async def delete_student(
    student_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin")),
):
    result = await db.execute(select(Student).where(Student.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    await db.delete(student)
    await db.commit()
    return {"success": True}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _student_to_dict(s: Student) -> dict:
    return {
        "id": str(s.id),
        "user_id": str(s.user_id) if s.user_id else None,
        "school_id": str(s.school_id),
        "student_number": s.student_number,
        "date_of_birth": str(s.date_of_birth) if s.date_of_birth else None,
        "gender": s.gender,
        "guardian_name": s.guardian_name,
        "guardian_email": s.guardian_email,
        "enrolled_at": s.enrolled_at.isoformat() if s.enrolled_at else None,
    }


def _course_to_dict(c: Course) -> dict:
    return {
        "id": str(c.id),
        "school_id": str(c.school_id),
        "teacher_id": str(c.teacher_id) if c.teacher_id else None,
        "academic_year_id": str(c.academic_year_id),
        "name": c.name,
        "subject": c.subject,
        "grade_level": c.grade_level,
        "credit_hours": c.credit_hours,
    }


def _grade_to_dict(g: Grade) -> dict:
    return {
        "id": str(g.id),
        "enrollment_id": str(g.enrollment_id),
        "assessment_type": g.assessment_type,
        "title": g.title,
        "score": g.score,
        "max_score": g.max_score,
        "weight": g.weight,
        "assessed_on": str(g.assessed_on) if g.assessed_on else None,
        "recorded_by": str(g.recorded_by) if g.recorded_by else None,
    }


def _attendance_to_dict(a: Attendance) -> dict:
    return {
        "id": str(a.id),
        "enrollment_id": str(a.enrollment_id),
        "date": str(a.date),
        "status": a.status,
        "note": a.note,
        "recorded_by": str(a.recorded_by) if a.recorded_by else None,
    }


def _prediction_to_dict(p: Prediction) -> dict:
    return {
        "id": str(p.id),
        "student_id": str(p.student_id),
        "course_id": str(p.course_id) if p.course_id else None,
        "predicted_grade": p.predicted_grade,
        "pass_probability": p.pass_probability,
        "risk_level": p.risk_level,
        "factors": p.factors,
        "recommendations": p.recommendations,
        "ai_summary": p.ai_summary,
        "generated_at": p.generated_at.isoformat() if p.generated_at else None,
    }


def _insight_to_dict(i: AiInsight) -> dict:
    return {
        "id": str(i.id),
        "student_id": str(i.student_id),
        "insight_type": i.insight_type,
        "content": i.content,
        "metadata": i.metadata_,
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }
