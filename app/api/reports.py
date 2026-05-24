from __future__ import annotations

import csv
import io
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.core.database import get_db
from app.models import Student, User, Enrollment, Course, Grade, Attendance
from app.core.security import require_auth
from app.deps import filter_enrollments_for_role, resolve_school_scope, student_visibility_clause

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/export")
async def export_report(
    school_id: uuid.UUID = Query(..., description="School ID"),
    format: str = Query("csv"),
    student_id: uuid.UUID | None = None,
    course_id: uuid.UUID | None = None,
    subject: str | None = None,
    assessment_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    school_id = resolve_school_scope(auth, school_id)
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
        .where(Student.school_id == school_id, student_visibility_clause(auth))
    )
    students = result.unique().scalars().all()

    filtered_students = []
    for s in students:
        if student_id and s.id != student_id:
            continue

        enrollments = []
        for e in filter_enrollments_for_role(s.enrollments, auth):
            if course_id and e.course_id != course_id:
                continue
            if subject and (not e.course or e.course.subject != subject):
                continue

            grades = []
            for g in e.grades or []:
                if assessment_type and g.assessment_type != assessment_type:
                    continue
                if date_from and g.assessed_on and g.assessed_on < date_from:
                    continue
                if date_to and g.assessed_on and g.assessed_on > date_to:
                    continue
                grades.append(g)

            attendance = []
            for a in e.attendance_records or []:
                if date_from and a.date and a.date < date_from:
                    continue
                if date_to and a.date and a.date > date_to:
                    continue
                attendance.append(a)

            if course_id or subject or assessment_type or date_from or date_to:
                if not grades and not attendance:
                    continue

            enrollments.append({
                "course": e.course,
                "grades": grades,
                "attendance_records": attendance,
            })

        filtered_students.append({
            "student_number": s.student_number,
            "user": s.user,
            "enrollments": enrollments,
        })

    students = filtered_students

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Student Number", "Name", "Email", "Course",
            "Assessment", "Title", "Score", "Max Score", "Date",
        ])
        for s in students:
            for e in s["enrollments"] or []:
                for g in e["grades"] or []:
                    writer.writerow([
                        s["student_number"],
                        s["user"].full_name if s["user"] else "",
                        s["user"].email if s["user"] else "",
                        e["course"].name if e["course"] else "",
                        g.assessment_type,
                        g.title,
                        g.score,
                        g.max_score,
                        g.assessed_on.isoformat() if g.assessed_on else "",
                    ])

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="ispps-export.csv"'},
        )

    # JSON format
    data = []
    for s in students:
        data.append({
            "student_number": s["student_number"],
            "user": {
                "full_name": s["user"].full_name if s["user"] else None,
                "email": s["user"].email if s["user"] else None,
            },
            "enrollments": [
                {
                    "course": {"name": e["course"].name, "subject": e["course"].subject} if e["course"] else None,
                    "grades": [
                        {
                            "assessment_type": g.assessment_type,
                            "title": g.title,
                            "score": g.score,
                            "max_score": g.max_score,
                            "assessed_on": g.assessed_on.isoformat() if g.assessed_on else None,
                        }
                        for g in e["grades"] or []
                    ],
                    "attendance": [
                        {"date": a.date.isoformat() if a.date else None, "status": a.status}
                        for a in e["attendance_records"] or []
                    ],
                }
                for e in s["enrollments"] or []
            ],
        })
    return data
