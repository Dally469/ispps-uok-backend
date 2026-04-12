from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models import Prediction, Student, User, Course
from app.schemas import PredictionCreate
from app.utils.auth import require_auth
from app.utils.access import course_visibility_clause, prediction_visibility_clause, resolve_school_scope, student_visibility_clause

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.get("")
async def list_predictions(
    request: Request,
    student_id: uuid.UUID | None = None,
    course_id: uuid.UUID | None = None,
    school_id: uuid.UUID | None = None,
    risk_level: str | None = None,
    search: str | None = None,
    min_predicted_grade: float | None = None,
    max_predicted_grade: float | None = None,
    generated_from: datetime | None = None,
    generated_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    school_scope = resolve_school_scope(auth, school_id)
    q = (
        select(Prediction)
        .options(
            joinedload(Prediction.student).joinedload(Student.user),
            joinedload(Prediction.course),
        )
        .order_by(Prediction.generated_at.desc())
        .where(prediction_visibility_clause(auth))
    )

    if school_scope:
        q = q.where(Prediction.student.has(Student.school_id == school_scope))
    if student_id:
        q = q.where(Prediction.student_id == student_id)
    if course_id:
        q = q.where(Prediction.course_id == course_id)
    if risk_level:
        q = q.where(Prediction.risk_level == risk_level)
    if search:
        term = f"%{search}%"
        q = q.where(
            Prediction.student.has(
                or_(
                    Student.student_number.ilike(term),
                    Student.user.has(or_(User.full_name.ilike(term), User.email.ilike(term))),
                )
            )
        )
    if min_predicted_grade is not None:
        q = q.where(Prediction.predicted_grade >= min_predicted_grade)
    if max_predicted_grade is not None:
        q = q.where(Prediction.predicted_grade <= max_predicted_grade)
    if generated_from:
        q = q.where(Prediction.generated_at >= generated_from)
    if generated_to:
        q = q.where(Prediction.generated_at <= generated_to)

    q = q.offset(offset).limit(limit)

    result = await db.execute(q)
    predictions = result.unique().scalars().all()

    return [_format_prediction(p) for p in predictions]


@router.post("")
async def create_prediction(
    body: PredictionCreate,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    student_result = await db.execute(
        select(Student.id).where(Student.id == body.student_id, student_visibility_clause(auth))
    )
    if not student_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Student not found")

    if body.course_id:
        course_result = await db.execute(
            select(Course.id).where(Course.id == body.course_id, course_visibility_clause(auth))
        )
        if not course_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Course not found")

    prediction = Prediction(
        student_id=body.student_id,
        course_id=body.course_id,
        predicted_grade=body.predicted_grade,
        pass_probability=body.pass_probability,
        risk_level=body.risk_level,
        factors=body.factors,
        recommendations=body.recommendations,
        ai_summary=body.ai_summary,
    )
    db.add(prediction)
    await db.commit()
    await db.refresh(prediction)

    return {
        "id": str(prediction.id),
        "student_id": str(prediction.student_id),
        "course_id": str(prediction.course_id) if prediction.course_id else None,
        "predicted_grade": prediction.predicted_grade,
        "pass_probability": prediction.pass_probability,
        "risk_level": prediction.risk_level,
        "factors": prediction.factors,
        "recommendations": prediction.recommendations,
        "ai_summary": prediction.ai_summary,
        "generated_at": prediction.generated_at.isoformat() if prediction.generated_at else None,
    }


def _format_prediction(p: Prediction) -> dict:
    student_data = None
    if p.student:
        student_data = {
            "id": str(p.student.id),
            "student_number": p.student.student_number,
            "user": {"full_name": p.student.user.full_name} if p.student.user else None,
        }

    course_data = None
    if p.course:
        course_data = {
            "id": str(p.course.id),
            "name": p.course.name,
            "subject": p.course.subject,
        }

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
        "student": student_data,
        "course": course_data,
    }
