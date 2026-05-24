"""Feature engineering for student performance prediction.

Each row represents one (student, course) pair. Features are derived from
grades and attendance records up to the prediction point.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from statistics import mean, pstdev
from typing import Iterable


FEATURE_NAMES = [
    "avg_score",
    "score_stddev",
    "min_score",
    "max_score",
    "num_assessments",
    "quiz_avg",
    "midterm_avg",
    "assignment_avg",
    "project_avg",
    "lab_avg",
    "attendance_rate",
    "absence_count",
    "late_count",
    "total_attendance_records",
    "credit_hours",
]


@dataclass
class StudentCourseFeatures:
    avg_score: float
    score_stddev: float
    min_score: float
    max_score: float
    num_assessments: int
    quiz_avg: float
    midterm_avg: float
    assignment_avg: float
    project_avg: float
    lab_avg: float
    attendance_rate: float
    absence_count: int
    late_count: int
    total_attendance_records: int
    credit_hours: int

    def to_vector(self) -> list[float]:
        return [getattr(self, name) for name in FEATURE_NAMES]

    def to_dict(self) -> dict:
        return asdict(self)


def _pct(score: float, max_score: float) -> float:
    return (score / max_score) * 100.0 if max_score else 0.0


def _avg_by_type(grades: Iterable, assessment_type: str) -> float:
    values = [_pct(g.score, g.max_score) for g in grades if g.assessment_type == assessment_type]
    return mean(values) if values else 0.0


def build_features(grades: list, attendance: list, credit_hours: int = 3) -> StudentCourseFeatures:
    """Build a feature vector from raw grade and attendance records.

    `grades` items must expose: score, max_score, assessment_type.
    `attendance` items must expose: status ('present'|'absent'|'late'|'excused').
    """
    score_pcts = [_pct(g.score, g.max_score) for g in grades]

    avg_score = mean(score_pcts) if score_pcts else 0.0
    score_stddev = pstdev(score_pcts) if len(score_pcts) > 1 else 0.0
    min_score = min(score_pcts) if score_pcts else 0.0
    max_score = max(score_pcts) if score_pcts else 0.0

    total_att = len(attendance)
    present = sum(1 for a in attendance if a.status == "present")
    absent = sum(1 for a in attendance if a.status == "absent")
    late = sum(1 for a in attendance if a.status == "late")
    attendance_rate = (present / total_att) * 100.0 if total_att else 0.0

    return StudentCourseFeatures(
        avg_score=round(avg_score, 2),
        score_stddev=round(score_stddev, 2),
        min_score=round(min_score, 2),
        max_score=round(max_score, 2),
        num_assessments=len(score_pcts),
        quiz_avg=round(_avg_by_type(grades, "quiz"), 2),
        midterm_avg=round(_avg_by_type(grades, "midterm"), 2),
        assignment_avg=round(_avg_by_type(grades, "assignment"), 2),
        project_avg=round(_avg_by_type(grades, "project"), 2),
        lab_avg=round(_avg_by_type(grades, "lab"), 2),
        attendance_rate=round(attendance_rate, 2),
        absence_count=absent,
        late_count=late,
        total_attendance_records=total_att,
        credit_hours=credit_hours,
    )


def risk_from_score(predicted_grade: float, pass_probability: float) -> str:
    """Map model outputs to a categorical risk level."""
    if predicted_grade < 40 or pass_probability < 0.25:
        return "critical"
    if predicted_grade < 55 or pass_probability < 0.5:
        return "high"
    if predicted_grade < 70 or pass_probability < 0.75:
        return "medium"
    return "low"
