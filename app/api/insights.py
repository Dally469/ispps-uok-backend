"""Replaces the previous Anthropic-powered router.

All "insights", "recommendations" and "risk scan" endpoints are now produced
deterministically from the trained ML model and rule-based summaries.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.database import get_db
from app.core.security import require_auth, require_role
from app.deps import (
    filter_enrollments_for_role,
    resolve_school_scope,
    student_visibility_clause,
)
from app.models import AiInsight, Enrollment, Student
from app.schemas import InsightsRequest, RecommendRequest
from ml.features import build_features
from ml.predict import StudentPredictor


router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.post("/summary")
async def performance_summary(
    body: InsightsRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    student = await _load_student(body.student_id, db, auth)
    enrollments = filter_enrollments_for_role(student.enrollments, auth)

    grades = [g for e in enrollments for g in e.grades]
    attendance = [a for e in enrollments for a in e.attendance_records]
    if not grades:
        raise HTTPException(status_code=422, detail="Not enough grade data for a summary.")

    feats = build_features(grades, attendance)
    summary = _summary_text(student, feats)

    insight = AiInsight(
        student_id=body.student_id,
        insight_type="performance",
        content=summary,
        metadata_={
            "grades_analyzed": len(grades),
            "attendance_records": len(attendance),
            "features": feats.to_dict(),
        },
    )
    db.add(insight)
    await db.commit()
    return {"summary": summary, "features": feats.to_dict()}


@router.post("/study-plan")
async def study_plan(
    body: RecommendRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    student = await _load_student(body.student_id, db, auth)
    enrollments = filter_enrollments_for_role(student.enrollments, auth)

    lines: list[str] = []
    for e in enrollments:
        if not e.course:
            continue
        grades = list(e.grades or [])
        attendance = list(e.attendance_records or [])
        if not grades:
            continue
        feats = build_features(grades, attendance, credit_hours=e.course.credit_hours)
        focus = "review fundamentals" if feats.avg_score < 60 else "practice and consolidation"
        course_label = f"{e.course.name} ({e.course.subject})"
        lines.append(f"{course_label}: current average {feats.avg_score:.1f}%, attendance {feats.attendance_rate:.1f}%.")
        lines.append(f"{course_label}: suggested focus this week is {focus}.")
        lines.append(f"{course_label}: allocate about {e.course.credit_hours * 2} hours of study time.")
        if feats.attendance_rate < 80:
            lines.append(f"{course_label}: attend every class — attendance is the biggest lift here.")
        if feats.assignment_avg and feats.assignment_avg < 60:
            lines.append(f"{course_label}: start assignments early and submit a draft for feedback.")

    plan = "\n".join(lines) or "No active enrolments with grade data yet."

    insight = AiInsight(
        student_id=body.student_id,
        insight_type="recommendation",
        content=plan,
        metadata_={"type": "study_plan"},
    )
    db.add(insight)
    await db.commit()
    return {"plan": plan}


_RISK_RANK = {"critical": 0, "high": 1, "medium": 2}


@router.get("/risk-scan")
async def risk_scan(
    school_id: uuid.UUID | None = None,
    course_id: uuid.UUID | None = None,
    risk_level: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "lecturer")),
):
    """Return one warning per (student, course) pair at medium-or-worse risk.

    Filters:
      - course_id: restrict to a single course
      - risk_level: one of medium | high | critical
      - search: matches student full_name or student_number (substring)

    Lecturer scope is enforced via `filter_enrollments_for_role` so a
    lecturer only ever sees rows for the courses they teach.
    """
    sid = resolve_school_scope(auth, school_id)
    if not sid:
        raise HTTPException(status_code=400, detail="school_id is required")

    result = await db.execute(
        select(Student)
        .options(
            joinedload(Student.user),
            selectinload(Student.enrollments).joinedload(Enrollment.course),
            selectinload(Student.enrollments).selectinload(Enrollment.grades),
            selectinload(Student.enrollments).selectinload(Enrollment.attendance_records),
        )
        .where(Student.school_id == sid, student_visibility_clause(auth))
    )
    students = result.unique().scalars().all()

    try:
        predictor = StudentPredictor.get()
    except FileNotFoundError:
        predictor = None

    search_term = (search or "").strip().lower()
    warnings: list[dict] = []
    visible_students: set[str] = set()

    for s in students:
        enrollments = filter_enrollments_for_role(s.enrollments, auth)
        if course_id:
            enrollments = [e for e in enrollments if e.course_id == course_id]
        if not enrollments:
            continue

        student_name = s.user.full_name if s.user else s.student_number
        if search_term:
            haystack = f"{student_name} {s.student_number}".lower()
            if search_term not in haystack:
                continue

        visible_students.add(str(s.id))

        for e in enrollments:
            grades = list(e.grades or [])
            attendance = list(e.attendance_records or [])
            if not grades:
                continue

            credit_hours = e.course.credit_hours if e.course else 3
            feats = build_features(grades, attendance, credit_hours=credit_hours)

            if predictor:
                output = predictor.predict(feats)
                level = output["risk_level"]
                predicted = output["predicted_grade"]
                pass_proba = output["pass_probability"]
                flags = [f["name"] for f in output["factors"] if f["impact"] == "negative"]
            else:
                # Fallback rule-based scoring per course.
                rule = _rule_only_warning(s, feats)
                level = rule["riskLevel"]
                predicted = feats.avg_score
                pass_proba = min(max(feats.avg_score / 100, 0), 1)
                flags = rule.get("flags", [])

            if level not in _RISK_RANK:
                continue
            if risk_level and level != risk_level:
                continue

            warnings.append({
                "student_id": str(s.id),
                "student_name": student_name,
                "student_number": s.student_number,
                "course_id": str(e.course.id) if e.course else None,
                "course_name": e.course.name if e.course else None,
                "course_subject": e.course.subject if e.course else None,
                "risk_level": level,
                "predicted_grade": predicted,
                "pass_probability": pass_proba,
                "avg_score": feats.avg_score,
                "attendance_rate": feats.attendance_rate,
                "num_assessments": feats.num_assessments,
                "flags": flags,
            })

    warnings.sort(key=lambda w: (_RISK_RANK[w["risk_level"]], -w["predicted_grade"] if w["predicted_grade"] else 0))
    critical = sum(1 for w in warnings if w["risk_level"] in ("critical", "high"))

    return {
        "total_students_visible": len(visible_students),
        "at_risk_rows": len(warnings),
        "critical_or_high": critical,
        "warnings": warnings,
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _load_student(student_id: uuid.UUID, db: AsyncSession, auth: dict) -> Student:
    result = await db.execute(
        select(Student)
        .options(
            joinedload(Student.user),
            selectinload(Student.enrollments).joinedload(Enrollment.course),
            selectinload(Student.enrollments).selectinload(Enrollment.grades),
            selectinload(Student.enrollments).selectinload(Enrollment.attendance_records),
        )
        .where(Student.id == student_id, student_visibility_clause(auth))
    )
    student = result.unique().scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


def _summary_text(student: Student, feats) -> str:
    name = student.user.full_name if student.user else student.student_number
    trend = "above target" if feats.avg_score >= 70 else "on track" if feats.avg_score >= 55 else "below target"
    attendance_note = (
        "excellent attendance" if feats.attendance_rate >= 90
        else "acceptable attendance" if feats.attendance_rate >= 75
        else "attendance is a concern"
    )
    consistency = "consistent" if feats.score_stddev <= 10 else "variable"
    return (
        f"{name} is currently {trend} with an average of {feats.avg_score:.1f}% "
        f"across {feats.num_assessments} assessments. Performance is {consistency} "
        f"(std dev {feats.score_stddev:.1f}). Attendance rate is {feats.attendance_rate:.1f}% "
        f"({attendance_note}). Strongest area: assignments at {feats.assignment_avg:.1f}%, "
        f"quizzes at {feats.quiz_avg:.1f}%."
    )


def _rule_only_warning(student: Student, feats) -> dict:
    score = 0
    flags: list[str] = []
    if feats.avg_score < 50:
        score += 40
        flags.append("Failing grades")
    elif feats.avg_score < 65:
        score += 20
        flags.append("Below average grades")
    if feats.attendance_rate < 60:
        score += 35
        flags.append("Critical attendance")
    elif feats.attendance_rate < 80:
        score += 15
        flags.append("Low attendance")
    level = (
        "critical" if score >= 60
        else "high" if score >= 40
        else "medium" if score >= 20
        else "low"
    )
    return {
        "student_id": str(student.id),
        "name": student.user.full_name if student.user else student.student_number,
        "avgScore": feats.avg_score,
        "attendanceRate": feats.attendance_rate,
        "riskLevel": level,
        "predictedGrade": feats.avg_score,
        "passProbability": min(max(feats.avg_score / 100, 0), 1),
        "flags": flags,
    }
