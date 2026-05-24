from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import and_, false, or_, true

from app.models import Attendance, Course, Enrollment, Prediction, Student


def auth_user_id(auth: dict) -> uuid.UUID:
    return uuid.UUID(auth["userId"])


def auth_school_id(auth: dict) -> uuid.UUID | None:
    school_id = auth.get("schoolId")
    return uuid.UUID(school_id) if school_id else None


def resolve_school_scope(auth: dict, requested_school_id: uuid.UUID | None) -> uuid.UUID | None:
    school_id = auth_school_id(auth)
    if requested_school_id and school_id and requested_school_id != school_id:
        raise HTTPException(status_code=403, detail="You can only access data for your school")
    return requested_school_id or school_id


def student_visibility_clause(auth: dict):
    role = auth.get("role")
    user_id = auth_user_id(auth)
    school_id = auth_school_id(auth)

    if role == "admin":
        return Student.school_id == school_id if school_id else true()

    if role == "lecturer":
        clause = Student.enrollments.any(Enrollment.course.has(Course.lecturer_id == user_id))
        return and_(Student.school_id == school_id, clause) if school_id else clause

    if role == "student":
        clause = Student.user_id == user_id
        return and_(Student.school_id == school_id, clause) if school_id else clause

    return false()


def course_visibility_clause(auth: dict):
    role = auth.get("role")
    user_id = auth_user_id(auth)
    school_id = auth_school_id(auth)

    if role == "admin":
        return Course.school_id == school_id if school_id else true()

    if role == "lecturer":
        clause = Course.lecturer_id == user_id
        return and_(Course.school_id == school_id, clause) if school_id else clause

    if role == "student":
        clause = Course.enrollments.any(Enrollment.student.has(Student.user_id == user_id))
        return and_(Course.school_id == school_id, clause) if school_id else clause

    return false()


def attendance_visibility_clause(auth: dict):
    role = auth.get("role")
    user_id = auth_user_id(auth)
    school_id = auth_school_id(auth)

    if role == "admin":
        if school_id:
            return Attendance.enrollment.has(Enrollment.student.has(Student.school_id == school_id))
        return true()

    if role == "lecturer":
        return Attendance.enrollment.has(Enrollment.course.has(Course.lecturer_id == user_id))

    if role == "student":
        return Attendance.enrollment.has(Enrollment.student.has(Student.user_id == user_id))

    return false()


def prediction_visibility_clause(auth: dict):
    role = auth.get("role")
    user_id = auth_user_id(auth)
    school_id = auth_school_id(auth)

    if role == "admin":
        if school_id:
            return Prediction.student.has(Student.school_id == school_id)
        return true()

    if role == "lecturer":
        direct_course_clause = Prediction.course.has(Course.lecturer_id == user_id)
        overall_student_clause = and_(
            Prediction.course_id.is_(None),
            Prediction.student.has(
                Student.enrollments.any(Enrollment.course.has(Course.lecturer_id == user_id))
            ),
        )
        clause = or_(direct_course_clause, overall_student_clause)
        if school_id:
            clause = and_(Prediction.student.has(Student.school_id == school_id), clause)
        return clause

    if role == "student":
        clause = Prediction.student.has(Student.user_id == user_id)
        if school_id:
            clause = and_(Prediction.student.has(Student.school_id == school_id), clause)
        return clause

    return false()


def filter_enrollments_for_role(enrollments: list[Enrollment] | None, auth: dict) -> list[Enrollment]:
    items = list(enrollments or [])
    if auth.get("role") != "lecturer":
        return items

    user_id = auth_user_id(auth)
    return [enrollment for enrollment in items if enrollment.course and enrollment.course.lecturer_id == user_id]
