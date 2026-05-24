from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.models import Enrollment, Grade, Course
from app.schemas import GradeCreate
from app.core.security import require_role, require_auth
from app.deps import auth_user_id

router = APIRouter(prefix="/api/grades", tags=["grades"]) 


@router.post("")
async def create_grade(
    body: GradeCreate,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "lecturer")),
):
    # verify enrollment exists
    result = await db.execute(
        select(Enrollment).where(Enrollment.id == body.enrollment_id).options(joinedload(Enrollment.course))
    )
    enrollment = result.unique().scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    # if lecturer, ensure they own the course
    if auth.get("role") == "lecturer":
        if not enrollment.course or enrollment.course.lecturer_id != uuid.UUID(auth.get("userId")):
            raise HTTPException(status_code=403, detail="You can only add grades for your courses")

    grade = Grade(
        enrollment_id=body.enrollment_id,
        assessment_type=body.assessment_type,
        title=body.title,
        score=body.score,
        max_score=body.max_score,
        weight=body.weight,
        assessed_on=body.assessed_on,
        recorded_by=uuid.UUID(auth.get("userId")),
    )
    db.add(grade)
    await db.commit()
    await db.refresh(grade)

    return {
        "id": str(grade.id),
        "enrollment_id": str(grade.enrollment_id),
        "assessment_type": grade.assessment_type,
        "title": grade.title,
        "score": grade.score,
        "max_score": grade.max_score,
        "weight": grade.weight,
        "assessed_on": str(grade.assessed_on) if grade.assessed_on else None,
        "recorded_by": str(grade.recorded_by) if grade.recorded_by else None,
    }
