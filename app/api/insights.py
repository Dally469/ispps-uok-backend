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

    lines = ["## Personalised Study Plan", ""]
    for e in enrollments:
        if not e.course:
            continue
        grades = list(e.grades or [])
        attendance = list(e.attendance_records or [])
        if not grades:
            continue
        feats = build_features(grades, attendance, credit_hours=e.course.credit_hours)
        focus = "review fundamentals" if feats.avg_score < 60 else "practice and consolidation"
        lines.append(f"### {e.course.name} ({e.course.subject})")
        lines.append(f"- Current average: **{feats.avg_score:.1f}%**, attendance **{feats.attendance_rate:.1f}%**")
        lines.append(f"- Suggested focus this week: {focus}")
        lines.append(f"- Allocate ~{e.course.credit_hours * 2} hours of study time")
        if feats.attendance_rate < 80:
            lines.append("- Attend every class — attendance is the biggest lift here")
        if feats.assignment_avg and feats.assignment_avg < 60:
            lines.append("- Start assignments early; submit a draft for feedback")
        lines.append("")

    plan = "\n".join(lines) or "No active enrolments with grade data."

    insight = AiInsight(
        student_id=body.student_id,
        insight_type="recommendation",
        content=plan,
        metadata_={"type": "study_plan"},
    )
    db.add(insight)
    await db.commit()
    return {"plan": plan}


@router.get("/risk-scan")
async def risk_scan(
    school_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "lecturer")),
):
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
    if not students:
        return {"total": 0, "atRisk": 0, "critical": 0, "warnings": []}

    try:
        predictor = StudentPredictor.get()
    except FileNotFoundError:
        predictor = None  # fall back to rule-only scoring

    warnings = []
    visible = 0
    for s in students:
        enrollments = filter_enrollments_for_role(s.enrollments, auth)
        if not enrollments:
            continue
        visible += 1
        grades = [g for e in enrollments for g in e.grades]
        attendance = [a for e in enrollments for a in e.attendance_records]
        if not grades:
            continue

        feats = build_features(grades, attendance)
        if predictor:
            output = predictor.predict(feats)
            warnings.append(
                {
                    "student_id": str(s.id),
                    "name": s.user.full_name if s.user else s.student_number,
                    "avgScore": feats.avg_score,
                    "attendanceRate": feats.attendance_rate,
                    "riskLevel": output["risk_level"],
                    "predictedGrade": output["predicted_grade"],
                    "passProbability": output["pass_probability"],
                    "flags": [f["name"] for f in output["factors"] if f["impact"] == "negative"],
                }
            )
        else:
            warnings.append(_rule_only_warning(s, feats))

    warnings = [w for w in warnings if w["riskLevel"] in ("medium", "high", "critical")]
    warnings.sort(key=lambda w: ("critical", "high", "medium").index(w["riskLevel"]))
    critical = sum(1 for w in warnings if w["riskLevel"] in ("critical", "high"))

    return {
        "total": visible,
        "atRisk": len(warnings),
        "critical": critical,
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
