from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.database import get_db
from app.models import Student, User, Enrollment, Course, Grade, Attendance, Prediction, AiInsight
from app.schemas import PredictRequest, InsightsRequest, RecommendRequest, ChatRequest
from app.utils.auth import require_auth, require_role
from app.utils.access import filter_enrollments_for_role, prediction_visibility_clause, resolve_school_scope, student_visibility_clause
from app.utils.claude import ask_claude, get_claude

router = APIRouter(prefix="/api/claude", tags=["claude"])


# ── Helper: load student with full context ───────────────────────────────────

async def _load_student(student_id: uuid.UUID, db: AsyncSession, auth: dict) -> Student:
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
        .where(Student.id == student_id, student_visibility_clause(auth))
    )
    student = result.unique().scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


# ── Chat (SSE streaming) ────────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    student_context = ""
    if body.student_id:
        student = await _load_student(body.student_id, db, auth)
        enrollments = filter_enrollments_for_role(student.enrollments, auth)
        all_grades = [g for e in enrollments for g in e.grades]
        all_att = [a for e in enrollments for a in e.attendance_records]
        present = sum(1 for a in all_att if a.status == "present")
        pct = f"{(present / len(all_att)) * 100:.1f}" if all_att else "N/A"
        student_context = (
            f"\n\nStudent Context:\n"
            f"Name: {student.user.full_name if student.user else 'Unknown'} ({student.student_number})\n"
            f"Courses: {', '.join(e.course.name for e in enrollments if e.course)}\n"
            f"Total Grades: {len(all_grades)}, Total Attendance Records: {len(all_att)}\n"
            f"Present Rate: {pct}%"
        )

    system_prompt = (
        "You are ISPPS AI Assistant — an intelligent academic advisor embedded in the "
        "Intelligent Student Performance Prediction System. You help teachers, students, "
        "and parents understand academic performance, provide study advice, explain predictions, "
        "and answer education-related questions. Be concise, helpful, and data-driven."
        f"{student_context}"
    )

    messages = []
    if body.history:
        for h in body.history[-10:]:
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": body.message})

    client = get_claude()

    async def event_generator():
        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield f"data: {json.dumps({'text': text})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Insights ─────────────────────────────────────────────────────────────────

@router.post("/insights")
async def insights(
    body: InsightsRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    student = await _load_student(body.student_id, db, auth)

    # Fetch recent predictions
    pred_result = await db.execute(
        select(Prediction)
        .where(Prediction.student_id == body.student_id)
        .where(prediction_visibility_clause(auth))
        .order_by(Prediction.generated_at.desc())
        .limit(5)
    )
    predictions = pred_result.scalars().all()

    enrollments = filter_enrollments_for_role(student.enrollments, auth)
    all_grades = [g for e in enrollments for g in e.grades]
    all_att = [a for e in enrollments for a in e.attendance_records]

    present = sum(1 for a in all_att if a.status == "present")
    absent = sum(1 for a in all_att if a.status == "absent")
    late = sum(1 for a in all_att if a.status == "late")

    grade_lines = "\n".join(
        f"- {g.title} ({g.assessment_type}): {g.score}/{g.max_score}"
        for g in all_grades[:20]
    )
    pred_lines = ""
    if predictions:
        pred_lines = "Recent Predictions:\n" + "\n".join(
            f"- Grade: {p.predicted_grade}, Risk: {p.risk_level}" for p in predictions
        )

    prompt = f"""Generate a comprehensive academic performance summary for this student:

Student: {student.user.full_name if student.user else 'Unknown'} ({student.student_number})
Enrolled in: {', '.join(e.course.name for e in enrollments if e.course)}

Grade Data ({len(all_grades)} assessments):
{grade_lines}

Attendance Records: {len(all_att)} entries
- Present: {present}
- Absent: {absent}
- Late: {late}

{pred_lines}

Provide:
1. A concise performance summary (2-3 paragraphs)
2. Key strengths identified
3. Areas needing improvement
4. Trend analysis (improving/declining/stable)
5. Specific actionable recommendations

Format as a natural language report — NOT JSON."""

    try:
        summary = ask_claude(
            prompt,
            "You are an academic advisor AI. Write clear, professional student performance "
            "summaries that are helpful for teachers and parents.",
        )

        # Save as AI insight
        insight = AiInsight(
            student_id=body.student_id,
            insight_type="performance",
            content=summary,
            metadata_={"grades_analyzed": len(all_grades), "attendance_records": len(all_att)},
        )
        db.add(insight)
        await db.commit()

        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service unavailable: {e}")


# ── Predict ──────────────────────────────────────────────────────────────────

@router.post("/predict")
async def predict(
    body: PredictRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    student = await _load_student(body.student_id, db, auth)
    enrollments = filter_enrollments_for_role(student.enrollments, auth)

    all_grades = [g for e in enrollments for g in e.grades]
    all_att = [a for e in enrollments for a in e.attendance_records]

    avg_score = (
        sum((g.score / g.max_score) * 100 for g in all_grades) / len(all_grades)
        if all_grades else 0
    )
    attendance_rate = (
        (sum(1 for a in all_att if a.status == "present") / len(all_att)) * 100
        if all_att else 0
    )

    course_perf = []
    for e in enrollments:
        grades = e.grades or []
        att = e.attendance_records or []
        c_avg = (sum((g.score / g.max_score) * 100 for g in grades) / len(grades)) if grades else 0
        c_att = (sum(1 for a in att if a.status == "present") / len(att) * 100) if att else 0
        course_perf.append({
            "course": e.course.name if e.course else "Unknown",
            "subject": e.course.subject if e.course else "Unknown",
            "avgScore": round(c_avg, 1),
            "attendanceRate": round(c_att, 1),
            "gradeCount": len(grades),
        })

    focus = ""
    if body.course_id:
        target = next((e for e in enrollments if e.course_id == body.course_id), None)
        if target and target.course:
            focus = f"Focus prediction on: {target.course.name}"
        else:
            focus = "Provide overall performance prediction"
    else:
        focus = "Provide overall performance prediction"

    perf_lines = "\n".join(
        f"- {c['course']} ({c['subject']}): Avg {c['avgScore']}%, Attendance {c['attendanceRate']}%, {c['gradeCount']} assessments"
        for c in course_perf
    )

    prompt = f"""Analyze this student's academic data and predict their performance:

Student: {student.user.full_name if student.user else 'Unknown'} ({student.student_number})
Overall Average Score: {avg_score:.1f}%
Overall Attendance Rate: {attendance_rate:.1f}%

Course Performance:
{perf_lines}

{focus}

Respond in this exact JSON format:
{{
  "predicted_grade": <number 0-100>,
  "pass_probability": <number 0-1>,
  "risk_level": "<low|medium|high|critical>",
  "factors": [
    {{"name": "<factor>", "score": <0-100>, "weight": <0-1>, "impact": "<positive|neutral|negative>"}}
  ],
  "recommendations": ["<recommendation 1>", "<recommendation 2>", "<recommendation 3>"],
  "ai_summary": "<2-3 sentence summary of the student's academic outlook>"
}}"""

    prediction_data: dict
    try:
        ai_response = ask_claude(
            prompt,
            "You are an educational analytics AI. Analyze student data and return predictions "
            "in the exact JSON format requested. Be data-driven and specific.",
        )
        import re
        json_match = re.search(r"\{[\s\S]*\}", ai_response)
        if json_match:
            prediction_data = json.loads(json_match.group(0))
        else:
            raise ValueError("No JSON in AI response")
    except Exception:
        # Fallback algorithmic prediction
        prediction_data = {
            "predicted_grade": round(avg_score, 1),
            "pass_probability": min(avg_score / 100 + 0.1, 1) if avg_score >= 50 else max(avg_score / 100 - 0.1, 0),
            "risk_level": "low" if avg_score >= 75 else "medium" if avg_score >= 60 else "high" if avg_score >= 40 else "critical",
            "factors": [
                {"name": "Grade Average", "score": avg_score, "weight": 0.4, "impact": "positive" if avg_score >= 60 else "negative"},
                {"name": "Attendance", "score": attendance_rate, "weight": 0.3, "impact": "positive" if attendance_rate >= 75 else "negative"},
                {"name": "Assessment Count", "score": min(len(all_grades) * 10, 100), "weight": 0.15, "impact": "positive" if len(all_grades) >= 5 else "neutral"},
                {"name": "Consistency", "score": 50, "weight": 0.15, "impact": "neutral"},
            ],
            "recommendations": [
                "Focus on improving weak subjects through additional study sessions" if avg_score < 60 else "Maintain current study habits",
                "Improve class attendance — aim for at least 90%" if attendance_rate < 80 else "Continue excellent attendance record",
                "Meet with academic advisor to discuss course load and goals",
            ],
            "ai_summary": f"Student has an average score of {avg_score:.1f}% with {attendance_rate:.1f}% attendance rate. {'Performance is satisfactory.' if avg_score >= 60 else 'Immediate intervention recommended.'}",
        }

    # Save prediction to database
    pred = Prediction(
        student_id=body.student_id,
        course_id=body.course_id,
        predicted_grade=prediction_data["predicted_grade"],
        pass_probability=prediction_data["pass_probability"],
        risk_level=prediction_data["risk_level"],
        factors=prediction_data["factors"],
        recommendations=prediction_data["recommendations"],
        ai_summary=prediction_data.get("ai_summary"),
    )
    db.add(pred)
    await db.commit()
    await db.refresh(pred)

    return {
        "id": str(pred.id),
        "student_id": str(pred.student_id),
        "course_id": str(pred.course_id) if pred.course_id else None,
        "predicted_grade": pred.predicted_grade,
        "pass_probability": pred.pass_probability,
        "risk_level": pred.risk_level,
        "factors": pred.factors,
        "recommendations": pred.recommendations,
        "ai_summary": pred.ai_summary,
        "generated_at": pred.generated_at.isoformat() if pred.generated_at else None,
    }


# ── Recommend ────────────────────────────────────────────────────────────────

@router.post("/recommend")
async def recommend(
    body: RecommendRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    student = await _load_student(body.student_id, db, auth)
    enrollments = filter_enrollments_for_role(student.enrollments, auth)
    all_grades = [g for e in enrollments for g in e.grades]

    course_details = []
    for e in enrollments:
        grades = e.grades or []
        avg = (sum((g.score / g.max_score) * 100 for g in grades) / len(grades)) if grades else 0
        course_details.append(
            f"{e.course.name if e.course else 'Unknown'} ({e.course.subject if e.course else '?'}): avg {avg:.1f}%"
        )

    prompt = f"""Create a personalized study plan for this student:

Student: {student.user.full_name if student.user else 'Unknown'}
Current Courses & Performance:
{chr(10).join(course_details)}

Total Assessments: {len(all_grades)}

Create a detailed weekly study plan that:
1. Prioritizes weakest subjects
2. Allocates time proportionally to credit hours
3. Includes specific study techniques for each subject
4. Suggests resources and practice activities
5. Includes break schedules and revision sessions
6. Sets weekly targets/milestones

Format as a clear, organized study plan."""

    try:
        plan = ask_claude(
            prompt,
            "You are an academic study coach. Create practical, detailed study plans "
            "that are realistic and actionable for university students.",
        )

        insight = AiInsight(
            student_id=body.student_id,
            insight_type="recommendation",
            content=plan,
            metadata_={"type": "study_plan"},
        )
        db.add(insight)
        await db.commit()

        return {"plan": plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service unavailable: {e}")


# ── Risk Assessment ──────────────────────────────────────────────────────────

@router.post("/risk")
async def risk_assessment(
    request: Request,
    school_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin", "teacher")),
):
    sid = resolve_school_scope(auth, school_id)
    if not sid:
        raise HTTPException(status_code=400, detail="school_id is required")

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

    if not students:
        return {"warnings": [], "summary": "No students found."}

    visible_students = 0
    at_risk = []
    for s in students:
        enrollments = filter_enrollments_for_role(s.enrollments, auth)
        if not enrollments:
            continue

        visible_students += 1

        grades = [g for e in enrollments for g in e.grades]
        att = [a for e in enrollments for a in e.attendance_records]

        avg_score = (sum((g.score / g.max_score) * 100 for g in grades) / len(grades)) if grades else None
        att_rate = (sum(1 for a in att if a.status == "present") / len(att) * 100) if att else None

        risk_score = 0
        flags: list[str] = []

        if avg_score is not None and avg_score < 50:
            risk_score += 40
            flags.append("Failing grades")
        elif avg_score is not None and avg_score < 65:
            risk_score += 20
            flags.append("Below average grades")

        if att_rate is not None and att_rate < 60:
            risk_score += 35
            flags.append("Critical attendance")
        elif att_rate is not None and att_rate < 80:
            risk_score += 15
            flags.append("Low attendance")

        if not grades:
            risk_score += 10
            flags.append("No grade data")

        if risk_score > 0:
            level = "critical" if risk_score >= 60 else "high" if risk_score >= 40 else "medium" if risk_score >= 20 else "low"
            at_risk.append({
                "student_id": str(s.id),
                "name": s.user.full_name if s.user else s.student_number,
                "avgScore": round(avg_score, 1) if avg_score is not None else None,
                "attendanceRate": round(att_rate, 1) if att_rate is not None else None,
                "riskScore": min(risk_score, 100),
                "riskLevel": level,
                "flags": flags,
            })

    at_risk.sort(key=lambda x: x["riskScore"], reverse=True)
    critical = [s for s in at_risk if s["riskLevel"] in ("critical", "high")]

    ai_summary = ""
    if critical:
        try:
            lines = "\n".join(
                f"- {s['name']}: Score {s['avgScore']}%, Attendance {s['attendanceRate']}%, "
                f"Risk {s['riskLevel']}, Flags: {', '.join(s['flags'])}"
                for s in critical[:10]
            )
            prompt = f"""Analyze these at-risk students and provide early warning recommendations:

{lines}

Provide:
1. Overview of the risk landscape
2. Priority interventions needed
3. Recommended actions for each critical student
4. Systemic patterns you notice

Be concise and actionable."""

            ai_summary = ask_claude(
                prompt,
                "You are an early warning system for academic institutions. "
                "Provide clear, prioritized intervention recommendations.",
            )
        except Exception:
            ai_summary = "AI analysis unavailable — review risk scores manually."

    return {
        "total": visible_students,
        "atRisk": len(at_risk),
        "critical": len(critical),
        "warnings": at_risk,
        "aiSummary": ai_summary,
    }
