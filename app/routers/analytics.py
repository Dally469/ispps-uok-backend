from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.database import get_db
from app.models import Student, User, Enrollment, Course, Grade, Attendance, Prediction
from app.utils.auth import require_auth
from app.utils.access import course_visibility_clause, filter_enrollments_for_role, prediction_visibility_clause, resolve_school_scope, student_visibility_clause

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
async def analytics_summary(
    request: Request,
    school_id: uuid.UUID | None = None,
    course_id: uuid.UUID | None = None,
    subject: str | None = None,
    risk_level: str | None = None,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    sid = resolve_school_scope(auth, school_id)
    if not sid:
        raise HTTPException(status_code=400, detail="school_id is required")

    # Fetch students with enrollments, grades, attendance
    result = await db.execute(
        select(Student)
        .options(
            joinedload(Student.user),
            selectinload(Student.enrollments)
            .joinedload(Enrollment.course),
            selectinload(Student.enrollments)
            .selectinload(Enrollment.grades),
            selectinload(Student.enrollments)
            .selectinload(Enrollment.attendance_records),
        )
        .where(Student.school_id == sid, student_visibility_clause(auth))
    )
    students = result.unique().scalars().all()

    scoped_students = []
    for student in students:
        enrollments = filter_enrollments_for_role(student.enrollments, auth)
        if course_id or subject:
            enrollments = [
                enrollment
                for enrollment in enrollments
                if (not course_id or enrollment.course_id == course_id)
                and (not subject or (enrollment.course and enrollment.course.subject == subject))
            ]
        if enrollments:
            scoped_students.append((student, enrollments))

    # Fetch predictions
    pred_query = (
        select(Prediction)
        .where(Prediction.student.has(Student.school_id == sid), prediction_visibility_clause(auth))
        .order_by(Prediction.generated_at.desc())
        .limit(100)
    )
    if course_id:
        pred_query = pred_query.where(Prediction.course_id == course_id)
    if risk_level:
        pred_query = pred_query.where(Prediction.risk_level == risk_level)
    if subject:
        pred_query = pred_query.where(Prediction.course.has(Course.subject == subject))

    pred_result = await db.execute(pred_query)
    predictions = pred_result.scalars().all()

    # Fetch courses
    course_query = select(Course).where(Course.school_id == sid, course_visibility_clause(auth))
    if course_id:
        course_query = course_query.where(Course.id == course_id)
    if subject:
        course_query = course_query.where(Course.subject == subject)

    course_result = await db.execute(course_query)
    courses = course_result.scalars().all()

    # Calculate stats
    total_students = len(scoped_students)
    total_courses = len(courses)

    total_score = 0.0
    total_grades = 0
    total_present = 0
    total_attendance = 0
    subject_scores: dict[str, dict] = {}

    for _, enrollments in scoped_students:
        for e in enrollments:
            subject = e.course.subject if e.course else "Unknown"
            for g in e.grades:
                pct = (g.score / g.max_score) * 100
                total_score += pct
                total_grades += 1
                if subject not in subject_scores:
                    subject_scores[subject] = {"total": 0.0, "count": 0}
                subject_scores[subject]["total"] += pct
                subject_scores[subject]["count"] += 1
            for a in e.attendance_records:
                total_attendance += 1
                if a.status == "present":
                    total_present += 1

    average_gpa = round((total_score / total_grades / 100) * 4, 2) if total_grades > 0 else 0

    # Risk distribution
    risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for p in predictions:
        if p.risk_level in risk_counts:
            risk_counts[p.risk_level] += 1

    # Grade distribution
    grade_buckets = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for p in predictions:
        g = p.predicted_grade
        if g >= 80:
            grade_buckets["A"] += 1
        elif g >= 65:
            grade_buckets["B"] += 1
        elif g >= 50:
            grade_buckets["C"] += 1
        elif g >= 40:
            grade_buckets["D"] += 1
        else:
            grade_buckets["F"] += 1

    attendance_rate = round((total_present / total_attendance) * 100, 1) if total_attendance > 0 else 0

    return {
        "totalStudents": total_students,
        "totalCourses": total_courses,
        "averageGPA": average_gpa,
        "atRiskCount": risk_counts["high"] + risk_counts["critical"],
        "attendanceRate": attendance_rate,
        "riskDistribution": risk_counts,
        "gradeDistribution": [{"grade": g, "count": c} for g, c in grade_buckets.items()],
        "departmentPerformance": [
            {
                "subject": subject,
                "avgScore": round(data["total"] / data["count"], 1),
            }
            for subject, data in subject_scores.items()
        ],
        "recentPredictions": [
            {
                "id": str(p.id),
                "risk_level": p.risk_level,
                "predicted_grade": p.predicted_grade,
                "generated_at": p.generated_at.isoformat() if p.generated_at else None,
            }
            for p in predictions[:5]
        ],
    }
