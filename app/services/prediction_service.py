"""Shared prediction logic.

Both `POST /api/predictions/generate` (manual button) and the grade-save
hooks call `run_prediction_for_student` here. The function:

  1. Loads the student + the target enrollments
  2. Builds the feature vector
  3. Calls the trained scikit-learn predictor
  4. Inserts a new `predictions` row
  5. Fans out notifications (student + lecturer(s) + admins) when the
     risk is high or critical

It returns `(prediction, notification_ids)`. The caller is responsible
for committing the session and scheduling the outbound emails via
BackgroundTasks. Returns `(None, [])` when the predictor cannot run
(no marks yet, or model artefact missing).
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.notify import notify_many
from app.models import Course, Enrollment, Notification, Prediction, Student, User
from ml.features import build_features
from ml.predict import StudentPredictor


HIGH_RISK_LEVELS = {"high", "critical"}


async def _load_student_with_data(db: AsyncSession, student_id: uuid.UUID) -> Student | None:
    result = await db.execute(
        select(Student)
        .options(
            joinedload(Student.user),
            selectinload(Student.enrollments).joinedload(Enrollment.course),
            selectinload(Student.enrollments).selectinload(Enrollment.grades),
            selectinload(Student.enrollments).selectinload(Enrollment.attendance_records),
        )
        .where(Student.id == student_id)
    )
    return result.unique().scalar_one_or_none()


async def _fanout_risk_notifications(
    db: AsyncSession,
    *,
    student: Student,
    prediction: Prediction,
    course: Course | None,
) -> list[Notification]:
    if prediction.risk_level not in HIGH_RISK_LEVELS:
        return []

    student_name = student.user.full_name if student.user else student.student_number
    course_part = f" in {course.name}" if course else ""
    title = f"At-risk prediction for {student_name}"
    body = (
        f"Predicted grade {prediction.predicted_grade:.1f}%, "
        f"pass probability {prediction.pass_probability * 100:.0f}%{course_part}. "
        f"Risk level: {prediction.risk_level}."
    )

    recipients: list = []
    if student.user_id:
        recipients.append(student.user_id)

    if course and course.lecturer_id:
        recipients.append(course.lecturer_id)
    else:
        lecturer_result = await db.execute(
            select(Course.lecturer_id)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .where(Enrollment.student_id == student.id, Course.lecturer_id.is_not(None))
            .distinct()
        )
        recipients.extend(lecturer_result.scalars().all())

    admin_result = await db.execute(
        select(User.id).where(
            User.role == "admin",
            User.school_id == student.school_id,
        )
    )
    recipients.extend(admin_result.scalars().all())

    return notify_many(
        db,
        recipient_ids=recipients,
        type="prediction",
        title=title,
        body=body,
    )


async def run_prediction_for_student(
    db: AsyncSession,
    *,
    student_id: uuid.UUID,
    course_id: uuid.UUID | None = None,
    student: Student | None = None,
) -> tuple[Prediction | None, list[Notification]]:
    """Run the trained model and persist a new prediction.

    Caller must commit the session after this returns. Notifications are
    flushed into the same session and returned so the caller can schedule
    outbound emails.
    """
    if student is None:
        student = await _load_student_with_data(db, student_id)
    if student is None:
        return None, []

    enrollments = list(student.enrollments or [])
    if course_id:
        target = next((e for e in enrollments if e.course_id == course_id), None)
        if target is None:
            return None, []
        target_enrollments = [target]
    else:
        target_enrollments = enrollments

    grades = [g for e in target_enrollments for g in e.grades]
    attendance = [a for e in target_enrollments for a in e.attendance_records]
    if not grades:
        return None, []

    credit_hours = (
        target_enrollments[0].course.credit_hours
        if target_enrollments and target_enrollments[0].course
        else 3
    )
    features = build_features(grades, attendance, credit_hours=credit_hours)

    try:
        predictor = StudentPredictor.get()
    except FileNotFoundError:
        return None, []

    output = predictor.predict(features)

    prediction = Prediction(
        student_id=student.id,
        course_id=course_id,
        predicted_grade=output["predicted_grade"],
        pass_probability=output["pass_probability"],
        risk_level=output["risk_level"],
        factors=output["factors"],
        recommendations=output["recommendations"],
        ai_summary=output["summary"],
    )
    db.add(prediction)
    await db.flush()

    course = target_enrollments[0].course if (course_id and target_enrollments) else None
    notes = await _fanout_risk_notifications(db, student=student, prediction=prediction, course=course)
    return prediction, notes
