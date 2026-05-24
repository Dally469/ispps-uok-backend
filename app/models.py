import uuid
from datetime import datetime, date

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Index, Integer,
    String, Text, UniqueConstraint, CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


# ── Schools ──────────────────────────────────────────────────────────────────

class School(Base):
    __tablename__ = "schools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    address = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    users = relationship("User", back_populates="school")
    academic_years = relationship("AcademicYear", back_populates="school")
    courses = relationship("Course", back_populates="school")
    students = relationship("Student", back_populates="school")


# ── Users ────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, unique=True, nullable=False)
    full_name = Column(Text, nullable=False)
    role = Column(Text, nullable=False)
    avatar_url = Column(Text)
    password_hash = Column(Text, nullable=False)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    school = relationship("School", back_populates="users")
    student = relationship("Student", back_populates="user", uselist=False)
    notifications = relationship("Notification", back_populates="recipient")

    __table_args__ = (
        CheckConstraint("role IN ('admin','lecturer','student')", name="ck_users_role"),
        Index("idx_users_email", "email"),
        Index("idx_users_role", "role"),
    )


# ── Academic Years ───────────────────────────────────────────────────────────

class AcademicYear(Base):
    __tablename__ = "academic_years"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    label = Column(Text, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)

    school = relationship("School", back_populates="academic_years")
    courses = relationship("Course", back_populates="academic_year")

    __table_args__ = (
        Index("idx_academic_years_school", "school_id"),
    )


# ── Courses ──────────────────────────────────────────────────────────────────

class Course(Base):
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    lecturer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    academic_year_id = Column(UUID(as_uuid=True), ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    subject = Column(Text, nullable=False)
    grade_level = Column(Text)
    credit_hours = Column(Integer, nullable=False, default=3)

    school = relationship("School", back_populates="courses")
    lecturer = relationship("User", foreign_keys=[lecturer_id])
    academic_year = relationship("AcademicYear", back_populates="courses")
    enrollments = relationship("Enrollment", back_populates="course")

    __table_args__ = (
        Index("idx_courses_school", "school_id"),
        Index("idx_courses_lecturer", "lecturer_id"),
    )


# ── Students ─────────────────────────────────────────────────────────────────

class Student(Base):
    __tablename__ = "students"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    school_id = Column(UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False)
    student_number = Column(Text, unique=True, nullable=False)
    date_of_birth = Column(Date)
    gender = Column(Text)
    guardian_name = Column(Text)
    guardian_email = Column(Text)
    enrolled_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="student")
    school = relationship("School", back_populates="students")
    enrollments = relationship("Enrollment", back_populates="student")
    predictions = relationship("Prediction", back_populates="student")
    ai_insights = relationship("AiInsight", back_populates="student")

    __table_args__ = (
        CheckConstraint("gender IN ('male','female','other')", name="ck_students_gender"),
        Index("idx_students_school", "school_id"),
        Index("idx_students_user", "user_id"),
    )


# ── Enrollments ──────────────────────────────────────────────────────────────

class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    enrolled_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    status = Column(Text, nullable=False, default="active")

    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")
    grades = relationship("Grade", back_populates="enrollment")
    attendance_records = relationship("Attendance", back_populates="enrollment")

    __table_args__ = (
        CheckConstraint("status IN ('active','dropped','completed')", name="ck_enrollments_status"),
        UniqueConstraint("student_id", "course_id"),
        Index("idx_enrollments_student", "student_id"),
        Index("idx_enrollments_course", "course_id"),
    )


# ── Grades ───────────────────────────────────────────────────────────────────

class Grade(Base):
    __tablename__ = "grades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False)
    assessment_type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    assessed_on = Column(Date, nullable=False, server_default=func.current_date())
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))

    enrollment = relationship("Enrollment", back_populates="grades")

    __table_args__ = (
        CheckConstraint(
            "assessment_type IN ('quiz','midterm','final','assignment','project','lab')",
            name="ck_grades_assessment_type",
        ),
        Index("idx_grades_enrollment", "enrollment_id"),
    )


# ── Attendance ───────────────────────────────────────────────────────────────

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enrollment_id = Column(UUID(as_uuid=True), ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(Text, nullable=False)
    note = Column(Text)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))

    enrollment = relationship("Enrollment", back_populates="attendance_records")

    __table_args__ = (
        CheckConstraint("status IN ('present','absent','late','excused')", name="ck_attendance_status"),
        UniqueConstraint("enrollment_id", "date"),
        Index("idx_attendance_enrollment", "enrollment_id"),
        Index("idx_attendance_date", "date"),
    )


# ── Predictions ──────────────────────────────────────────────────────────────

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id", ondelete="SET NULL"))
    predicted_grade = Column(Float, nullable=False)
    pass_probability = Column(Float, nullable=False)
    risk_level = Column(Text, nullable=False)
    factors = Column(JSONB, nullable=False, default=list)
    recommendations = Column(JSONB, nullable=False, default=list)
    ai_summary = Column(Text)
    generated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    student = relationship("Student", back_populates="predictions")
    course = relationship("Course")

    __table_args__ = (
        CheckConstraint("risk_level IN ('low','medium','high','critical')", name="ck_predictions_risk"),
        Index("idx_predictions_student", "student_id"),
        Index("idx_predictions_course", "course_id"),
        Index("idx_predictions_risk", "risk_level"),
    )


# ── AI Insights ──────────────────────────────────────────────────────────────

class AiInsight(Base):
    __tablename__ = "ai_insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    insight_type = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    student = relationship("Student", back_populates="ai_insights")

    __table_args__ = (
        CheckConstraint(
            "insight_type IN ('performance','behavior','recommendation','warning','trend')",
            name="ck_ai_insights_type",
        ),
        Index("idx_ai_insights_student", "student_id"),
        Index("idx_ai_insights_type", "insight_type"),
    )


# ── Notifications ────────────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    recipient = relationship("User", back_populates="notifications")

    __table_args__ = (
        CheckConstraint(
            "type IN ('prediction','warning','grade','attendance','system')",
            name="ck_notifications_type",
        ),
        Index("idx_notifications_recipient", "recipient_id"),
    )


# ── Password reset tokens ────────────────────────────────────────────────────

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(Text, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_password_reset_token", "token"),
        Index("idx_password_reset_user", "user_id"),
    )
