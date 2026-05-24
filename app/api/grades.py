from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_db
from app.core.notify import email_notifications, notify_many
from app.core.security import require_auth, require_role
from app.deps import auth_user_id
from app.models import Course, Enrollment, Grade, Notification, Student
from app.schemas import BulkGradeRequest, GradeCreate, GradeUpdate
from app.services.prediction_service import run_prediction_for_student


router = APIRouter(prefix="/api/grades", tags=["grades"])
log = logging.getLogger("ispps.grades")

PASS_THRESHOLD_PCT = 50.0


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _load_enrollment(db: AsyncSession, enrollment_id: uuid.UUID) -> Enrollment:
    result = await db.execute(
        select(Enrollment)
        .options(
            joinedload(Enrollment.course),
            joinedload(Enrollment.student).joinedload(Student.user),
        )
        .where(Enrollment.id == enrollment_id)
    )
    enrollment = result.unique().scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return enrollment


def _fail_pct(score: float, max_score: float) -> float | None:
    """Returns the percentage if the mark is a fail, otherwise None."""
    if not max_score:
        return None
    pct = (score / max_score) * 100.0
    return pct if pct < PASS_THRESHOLD_PCT else None


def _notify_fail(
    db: AsyncSession,
    *,
    recipient_user_id: uuid.UUID | None,
    course_name: str,
    assessment_type: str,
    title: str,
    score: float,
    max_score: float,
) -> list[Notification]:
    if recipient_user_id is None:
        return []
    pct = (score / max_score) * 100.0
    return notify_many(
        db,
        recipient_ids=[recipient_user_id],
        type="grade",
        title=f"Failing mark in {course_name}",
        body=(
            f"{assessment_type.capitalize()} '{title}' was marked "
            f"{score:g}/{max_score:g} ({pct:.0f}%). "
            f"Below the {PASS_THRESHOLD_PCT:.0f}% pass threshold."
        ),
    )


async def _autopredict_after_marks(
    db: AsyncSession,
    *,
    student_id: uuid.UUID,
    course_id: uuid.UUID,
    background_tasks: BackgroundTasks,
) -> None:
    """Run the ML model after a mark has been saved. Failures are
    swallowed so they never break the grade request."""
    try:
        prediction, risk_notes = await run_prediction_for_student(
            db, student_id=student_id, course_id=course_id
        )
        if prediction is None:
            return
        await db.commit()
        if risk_notes:
            background_tasks.add_task(
                email_notifications, [n.id for n in risk_notes]
            )
    except Exception as exc:
        await db.rollback()
        log.warning("auto-predict failed for student=%s course=%s: %s", student_id, course_id, exc)


def _assert_can_grade(enrollment: Enrollment, auth: dict) -> None:
    if auth.get("role") == "lecturer":
        if not enrollment.course or enrollment.course.lecturer_id != auth_user_id(auth):
            raise HTTPException(status_code=403, detail="You can only grade your own courses")


def _format(g: Grade) -> dict:
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


# ── List ─────────────────────────────────────────────────────────────────────

@router.get("")
async def list_grades(
    enrollment_id: uuid.UUID | None = None,
    student_id: uuid.UUID | None = None,
    course_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    q = (
        select(Grade)
        .join(Enrollment, Grade.enrollment_id == Enrollment.id)
        .order_by(Grade.assessed_on.desc(), Grade.title)
    )
    if enrollment_id:
        q = q.where(Grade.enrollment_id == enrollment_id)
    if student_id:
        q = q.where(Enrollment.student_id == student_id)
    if course_id:
        q = q.where(Enrollment.course_id == course_id)

    role = auth.get("role")
    if role == "lecturer":
        q = q.where(Enrollment.course.has(Course.lecturer_id == auth_user_id(auth)))
    elif role == "student":
        q = q.where(Enrollment.student.has(Student.user_id == auth_user_id(auth)))

    result = await db.execute(q)
    return [_format(g) for g in result.scalars().all()]


# ── Create ───────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
async def create_grade(
    body: GradeCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "lecturer")),
):
    enrollment = await _load_enrollment(db, body.enrollment_id)
    _assert_can_grade(enrollment, auth)

    if body.score > body.max_score:
        raise HTTPException(status_code=422, detail="Score cannot exceed max score")

    grade = Grade(
        enrollment_id=body.enrollment_id,
        assessment_type=body.assessment_type,
        title=body.title,
        score=body.score,
        max_score=body.max_score,
        weight=body.weight,
        assessed_on=body.assessed_on,
        recorded_by=auth_user_id(auth),
    )
    db.add(grade)

    # Fail-mark notification (same transaction as the grade).
    fail_notes: list[Notification] = []
    if _fail_pct(body.score, body.max_score) is not None:
        course_name = enrollment.course.name if enrollment.course else "your course"
        recipient = enrollment.student.user_id if enrollment.student else None
        fail_notes = _notify_fail(
            db,
            recipient_user_id=recipient,
            course_name=course_name,
            assessment_type=body.assessment_type,
            title=body.title,
            score=body.score,
            max_score=body.max_score,
        )

    await db.commit()
    await db.refresh(grade)

    if fail_notes:
        background_tasks.add_task(email_notifications, [n.id for n in fail_notes])

    # Auto-run the ML prediction (silent — its own try/except + commit).
    if enrollment.student_id:
        await _autopredict_after_marks(
            db,
            student_id=enrollment.student_id,
            course_id=enrollment.course_id,
            background_tasks=background_tasks,
        )

    return _format(grade)


# ── Bulk create ──────────────────────────────────────────────────────────────

@router.post("/bulk", status_code=201)
async def bulk_create_grades(
    body: BulkGradeRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "lecturer")),
):
    """Record one assessment (e.g. 'Quiz 1') for many students at once.

    Every enrollment_id in `rows` must belong to the same `course_id`, which
    must be a course the caller is allowed to manage.
    """
    course_result = await db.execute(select(Course).where(Course.id == body.course_id))
    course = course_result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    if auth.get("role") == "lecturer" and course.lecturer_id != auth_user_id(auth):
        raise HTTPException(status_code=403, detail="You can only grade your own courses")

    enrollment_ids = [row.enrollment_id for row in body.rows]
    # Fetch enrollments + linked student.user_id for fail notifications + auto-predict.
    enr_result = await db.execute(
        select(Enrollment.id, Enrollment.course_id, Enrollment.student_id, Student.user_id)
        .join(Student, Student.id == Enrollment.student_id)
        .where(Enrollment.id.in_(enrollment_ids))
    )
    enrollment_info = {row.id: row for row in enr_result.all()}
    missing = [eid for eid in enrollment_ids if eid not in enrollment_info]
    if missing:
        raise HTTPException(status_code=404, detail=f"{len(missing)} enrollment(s) not found")
    wrong_course = [eid for eid, info in enrollment_info.items() if info.course_id != body.course_id]
    if wrong_course:
        raise HTTPException(status_code=422, detail="All enrollments must belong to the same course")

    recorded_by = auth_user_id(auth)
    created = 0
    skipped: list[str] = []
    fail_notes: list[Notification] = []
    affected_students: set[uuid.UUID] = set()

    for row in body.rows:
        if row.score > body.max_score:
            skipped.append(f"{row.enrollment_id}: score above max")
            continue
        grade = Grade(
            enrollment_id=row.enrollment_id,
            assessment_type=body.assessment_type,
            title=body.title,
            score=row.score,
            max_score=body.max_score,
            weight=body.weight,
            assessed_on=body.assessed_on,
            recorded_by=recorded_by,
        )
        db.add(grade)
        created += 1

        info = enrollment_info[row.enrollment_id]
        affected_students.add(info.student_id)

        # Fail-mark notification for this student.
        if _fail_pct(row.score, body.max_score) is not None:
            fail_notes.extend(_notify_fail(
                db,
                recipient_user_id=info.user_id,
                course_name=course.name,
                assessment_type=body.assessment_type,
                title=body.title,
                score=row.score,
                max_score=body.max_score,
            ))

    await db.commit()

    if fail_notes:
        background_tasks.add_task(email_notifications, [n.id for n in fail_notes])

    # Auto-predict for every affected student (course-scoped).
    for sid in affected_students:
        await _autopredict_after_marks(
            db,
            student_id=sid,
            course_id=body.course_id,
            background_tasks=background_tasks,
        )

    return {"created": created, "skipped": skipped, "fail_notifications": len(fail_notes)}


# ── Update ───────────────────────────────────────────────────────────────────

@router.put("/{grade_id}")
async def update_grade(
    grade_id: uuid.UUID,
    body: GradeUpdate,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "lecturer")),
):
    result = await db.execute(
        select(Grade)
        .options(joinedload(Grade.enrollment).joinedload(Enrollment.course))
        .where(Grade.id == grade_id)
    )
    grade = result.unique().scalar_one_or_none()
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    _assert_can_grade(grade.enrollment, auth)

    update_data = body.model_dump(exclude_unset=True)

    new_score    = update_data.get("score",    grade.score)
    new_max      = update_data.get("max_score", grade.max_score)
    if new_score > new_max:
        raise HTTPException(status_code=422, detail="Score cannot exceed max score")

    for field, value in update_data.items():
        setattr(grade, field, value)

    await db.commit()
    await db.refresh(grade)
    return _format(grade)


# ── Delete ───────────────────────────────────────────────────────────────────

@router.delete("/{grade_id}")
async def delete_grade(
    grade_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "lecturer")),
):
    result = await db.execute(
        select(Grade)
        .options(joinedload(Grade.enrollment).joinedload(Enrollment.course))
        .where(Grade.id == grade_id)
    )
    grade = result.unique().scalar_one_or_none()
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    _assert_can_grade(grade.enrollment, auth)

    await db.delete(grade)
    await db.commit()
    return {"success": True}
