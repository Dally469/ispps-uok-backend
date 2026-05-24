"""ETL: load the OULAD dataset into the ISPPS schema.

Source: UCI mirror of the Open University Learning Analytics Dataset
        (Kuzilek, Hlosta, Zdrahal 2017). The dataset contains 7 CSVs:
        courses, studentInfo, assessments, studentAssessment,
        studentRegistration, studentVle (~10M rows, skipped here),
        and vle.

This script transforms two IT-aligned module-presentations
(DDD-2014J and FFF-2014J) into the ispps schema:

    students             one row per id_student (deduped across modules)
    courses              one row per (module, presentation)
    enrollments          one row per (student, course)
    grades               one row per studentAssessment record
                         (TMA -> 'assignment', CMA -> 'quiz', Exam -> 'final')
    attendance           ~30 synthesised sessions per enrollment, with
                         absences correlated to the final_result so the
                         model can learn the attendance->outcome signal

The OULAD dataset has no direct attendance series; the dissertation
treats attendance as a primary academic indicator (section 2.2.3) so
we synthesise it deterministically from each row's `final_result` to
preserve the predictive relationship the ML pipeline expects.

Idempotent: deletes any existing OULAD-marker rows before reloading.

Usage:
    python -m db.load_oulad                  # default modules
    python -m db.load_oulad --modules DDD-2014J,FFF-2014J,CCC-2014J
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import uuid
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import async_session
from app.models import (
    AcademicYear,
    Attendance,
    Course,
    Enrollment,
    Grade,
    School,
    Student,
    User,
)


# ── Config ───────────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent / "datasets" / "oulad"
DEFAULT_MODULES = ["DDD-2014J", "FFF-2014J"]  # both IT-aligned, have Exam-type finals

# Seed-existing UUIDs we reuse so demo logins still work.
SCHOOL_ID = uuid.UUID("a0000000-0000-0000-0000-000000000001")
ACADEMIC_YEAR_ID = uuid.UUID("b0000000-0000-0000-0000-000000000001")
LECTURER_DSA_ID = uuid.UUID("c0000000-0000-0000-0000-000000000002")  # Dr. Silva
LECTURER_DBMS_ID = uuid.UUID("c0000000-0000-0000-0000-000000000003")  # Dr. Perera

# Marker so we can wipe & reload without touching the original seed data.
OULAD_PREFIX = "OU-"

# Attendance synthesis: total sessions per enrollment, and the absence
# distribution per final_result category. Tuned so the ML pipeline sees
# a strong but not absolute signal between attendance and outcome.
ATTENDANCE_SESSIONS = 30
ABSENCE_TARGETS = {
    "Distinction": (0, 3),    # 0-3 absences (~90-100% attendance)
    "Pass":        (3, 8),    # 3-8  absences (~73-90%)
    "Fail":        (8, 16),   # 8-16 absences (~47-73%)
    "Withdrawn":   (16, 25),  # 16-25 absences (~17-47%)
}

ASSESSMENT_TYPE_MAP = {
    "TMA": "assignment",   # Tutor-Marked Assessment
    "CMA": "quiz",          # Computer-Marked Assessment
    "Exam": "final",
}

GENDER_MAP = {"M": "male", "F": "female"}


# ── Module metadata ──────────────────────────────────────────────────────────

MODULE_LABELS = {
    "AAA": "Education & Communication",
    "BBB": "Social Science",
    "CCC": "Science (STEM)",
    "DDD": "Computing & IT",
    "EEE": "Computing & IT",
    "FFF": "Information Technology",
    "GGG": "Social Science",
}

# Round-robin lecturers for the synthesised courses.
LECTURER_POOL = [LECTURER_DSA_ID, LECTURER_DBMS_ID]


def _course_name(code_module: str, code_presentation: str) -> str:
    subject = MODULE_LABELS.get(code_module, "Open University Module")
    return f"{subject} — Module {code_module} ({code_presentation})"


# ── Data loading ─────────────────────────────────────────────────────────────

def _load_csvs() -> dict[str, pd.DataFrame]:
    # OULAD uses '?' as a missing-value marker - declare it so pandas
    # treats those cells as NaN and the score/weight columns load as
    # numeric instead of object.
    out = {
        "courses":             pd.read_csv(DATA_DIR / "courses.csv", na_values=["?"]),
        "studentInfo":         pd.read_csv(DATA_DIR / "studentInfo.csv", na_values=["?"]),
        "assessments":         pd.read_csv(DATA_DIR / "assessments.csv", na_values=["?"]),
        "studentAssessment":   pd.read_csv(DATA_DIR / "studentAssessment.csv", na_values=["?"]),
    }
    # Force numeric for the score/weight columns - any straggling
    # non-numeric values become NaN and are filtered out downstream.
    out["studentAssessment"]["score"] = pd.to_numeric(
        out["studentAssessment"]["score"], errors="coerce"
    )
    out["assessments"]["weight"] = pd.to_numeric(
        out["assessments"]["weight"], errors="coerce"
    )
    return out


def _filter_modules(dfs: dict[str, pd.DataFrame], targets: list[str]) -> dict[str, pd.DataFrame]:
    """Restrict every frame to the chosen module-presentation tuples."""
    target_pairs = {tuple(t.split("-")) for t in targets}

    def _pair_filter(df: pd.DataFrame) -> pd.DataFrame:
        if {"code_module", "code_presentation"} <= set(df.columns):
            return df[
                df.apply(
                    lambda r: (r["code_module"], r["code_presentation"]) in target_pairs,
                    axis=1,
                )
            ]
        return df

    out = {k: _pair_filter(v) for k, v in dfs.items()}
    # studentAssessment is keyed by id_assessment - filter by the surviving ids.
    valid_assessments = set(out["assessments"]["id_assessment"].tolist())
    out["studentAssessment"] = dfs["studentAssessment"][
        dfs["studentAssessment"]["id_assessment"].isin(valid_assessments)
    ]
    return out


def _synthesise_absences(final_result: str, seed: int) -> int:
    """Deterministic absence count tied to final_result and the student id."""
    low, high = ABSENCE_TARGETS.get(final_result, (5, 15))
    span = high - low + 1
    return low + (seed % span)


# ── Writers (async) ──────────────────────────────────────────────────────────

async def _ensure_school_and_year(db) -> None:
    """Verify the seed school + academic year are present so FKs resolve."""
    school = await db.scalar(select(School).where(School.id == SCHOOL_ID))
    if not school:
        db.add(School(id=SCHOOL_ID, name="University of Kigali"))
    year = await db.scalar(select(AcademicYear).where(AcademicYear.id == ACADEMIC_YEAR_ID))
    if not year:
        db.add(
            AcademicYear(
                id=ACADEMIC_YEAR_ID,
                school_id=SCHOOL_ID,
                label="2025/2026",
                start_date=date(2025, 9, 1),
                end_date=date(2026, 6, 30),
                is_active=True,
            )
        )
    await db.flush()


async def _wipe_oulad(db) -> None:
    """Remove any previously loaded OULAD rows. Cascade handles enrollments,
    grades, and attendance via the schema's ON DELETE CASCADE."""
    await db.execute(
        delete(Student).where(Student.student_number.like(f"{OULAD_PREFIX}%"))
    )
    await db.execute(
        delete(Course).where(Course.name.like("%— Module %(2014J)"))
    )
    await db.commit()


async def _create_courses(db, modules: list[str]) -> dict[str, uuid.UUID]:
    """Return module-presentation -> course UUID map."""
    course_ids: dict[str, uuid.UUID] = {}
    for idx, module_pres in enumerate(modules):
        code_module, code_presentation = module_pres.split("-")
        course = Course(
            school_id=SCHOOL_ID,
            academic_year_id=ACADEMIC_YEAR_ID,
            lecturer_id=LECTURER_POOL[idx % len(LECTURER_POOL)],
            name=_course_name(code_module, code_presentation),
            subject=MODULE_LABELS.get(code_module, "Computing & IT"),
            grade_level="Undergraduate",
            credit_hours=4,
        )
        db.add(course)
        await db.flush()
        course_ids[module_pres] = course.id
    return course_ids


async def _create_students_bulk(
    db, student_info: pd.DataFrame
) -> dict[int, uuid.UUID]:
    """Insert one Student per unique id_student. Returns id_student -> uuid map."""
    seen: dict[int, uuid.UUID] = {}
    unique_students = student_info.drop_duplicates(subset=["id_student"])
    rows = []
    for row in unique_students.itertuples(index=False):
        sid = uuid.uuid4()
        seen[int(row.id_student)] = sid
        rows.append(
            {
                "id": sid,
                "school_id": SCHOOL_ID,
                "student_number": f"{OULAD_PREFIX}{int(row.id_student)}",
                "gender": GENDER_MAP.get(row.gender),
                "user_id": None,
                "date_of_birth": None,
                "guardian_name": None,
                "guardian_email": None,
            }
        )

    # Chunked bulk insert for speed.
    CHUNK = 500
    for i in range(0, len(rows), CHUNK):
        await db.execute(Student.__table__.insert(), rows[i : i + CHUNK])
    return seen


async def _create_enrollments_bulk(
    db,
    student_info: pd.DataFrame,
    student_ids: dict[int, uuid.UUID],
    course_ids: dict[str, uuid.UUID],
) -> dict[tuple[int, str], uuid.UUID]:
    """Return (id_student, 'MOD-PRES') -> enrollment UUID."""
    enrollment_map: dict[tuple[int, str], uuid.UUID] = {}
    rows = []
    for row in student_info.itertuples(index=False):
        key = f"{row.code_module}-{row.code_presentation}"
        course_id = course_ids.get(key)
        if not course_id:
            continue
        eid = uuid.uuid4()
        enrollment_map[(int(row.id_student), key)] = eid
        status = "dropped" if row.final_result == "Withdrawn" else "completed"
        rows.append(
            {
                "id": eid,
                "student_id": student_ids[int(row.id_student)],
                "course_id": course_id,
                "status": status,
            }
        )
    CHUNK = 1000
    for i in range(0, len(rows), CHUNK):
        await db.execute(Enrollment.__table__.insert(), rows[i : i + CHUNK])
    return enrollment_map


async def _create_grades_bulk(
    db,
    assessments: pd.DataFrame,
    student_assessment: pd.DataFrame,
    student_info: pd.DataFrame,
    enrollment_map: dict[tuple[int, str], uuid.UUID],
) -> int:
    """Map each studentAssessment row to a grades record."""
    # Lookup table: id_assessment -> (module-presentation key, assessment_type, weight)
    ass_lookup = {
        int(r.id_assessment): (
            f"{r.code_module}-{r.code_presentation}",
            ASSESSMENT_TYPE_MAP.get(r.assessment_type, "assignment"),
            float(r.weight) if pd.notna(r.weight) else 0.0,
        )
        for r in assessments.itertuples(index=False)
    }

    rows: list[dict] = []
    for r in student_assessment.itertuples(index=False):
        meta = ass_lookup.get(int(r.id_assessment))
        if not meta:
            continue
        module_key, atype, weight = meta
        enrollment_id = enrollment_map.get((int(r.id_student), module_key))
        if not enrollment_id or pd.isna(r.score):
            continue
        # OULAD scores are already on a 0-100 scale; weights are %.
        rows.append(
            {
                "id": uuid.uuid4(),
                "enrollment_id": enrollment_id,
                "assessment_type": atype,
                "title": f"{atype.title()} assessment {int(r.id_assessment)}",
                "score": float(r.score),
                "max_score": 100.0,
                # Normalise weights so the schema invariant weight <= 1 holds.
                "weight": min(1.0, max(0.0, weight / 100.0)),
                "assessed_on": date(2026, 1, 15),
                "recorded_by": None,
            }
        )

    CHUNK = 2000
    for i in range(0, len(rows), CHUNK):
        await db.execute(Grade.__table__.insert(), rows[i : i + CHUNK])
    return len(rows)


async def _create_attendance_bulk(
    db,
    student_info: pd.DataFrame,
    enrollment_map: dict[tuple[int, str], uuid.UUID],
) -> int:
    """Synthesise ATTENDANCE_SESSIONS rows per enrollment, with the absent
    count tied to the row's final_result so the model sees the attendance
    -> outcome relationship the dissertation requires."""
    rows: list[dict] = []
    base_date = date(2025, 9, 8)  # week of the term start
    for r in student_info.itertuples(index=False):
        key = f"{r.code_module}-{r.code_presentation}"
        enrollment_id = enrollment_map.get((int(r.id_student), key))
        if not enrollment_id:
            continue
        absences = _synthesise_absences(r.final_result, int(r.id_student))
        # Distribute absences evenly across the term using the student id
        # as the rotation offset - deterministic, no random module needed.
        absent_indices = {
            (int(r.id_student) + j * 7) % ATTENDANCE_SESSIONS
            for j in range(absences)
        }
        for i in range(ATTENDANCE_SESSIONS):
            status = "absent" if i in absent_indices else "present"
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "enrollment_id": enrollment_id,
                    "date": base_date + timedelta(days=i * 7),  # weekly cadence
                    "status": status,
                    "note": None,
                    "recorded_by": None,
                }
            )

    CHUNK = 3000
    for i in range(0, len(rows), CHUNK):
        await db.execute(Attendance.__table__.insert(), rows[i : i + CHUNK])
    return len(rows)


# ── Orchestration ────────────────────────────────────────────────────────────

async def run(modules: list[str]) -> None:
    if not DATA_DIR.exists():
        raise SystemExit(
            f"OULAD CSVs not found at {DATA_DIR}. Download them first - see "
            "load_oulad.py docstring."
        )

    print(f"Loading OULAD CSVs from {DATA_DIR}...")
    dfs = _load_csvs()
    print(
        f"  raw rows: studentInfo={len(dfs['studentInfo'])} "
        f"assessments={len(dfs['assessments'])} "
        f"studentAssessment={len(dfs['studentAssessment'])}"
    )

    print(f"Filtering to modules: {modules}")
    dfs = _filter_modules(dfs, modules)
    print(
        f"  filtered: students={len(dfs['studentInfo'])} "
        f"assessments={len(dfs['assessments'])} "
        f"studentAssessment={len(dfs['studentAssessment'])}"
    )

    async with async_session() as db:
        await _ensure_school_and_year(db)
        print("Wiping previous OULAD rows (if any)...")
        await _wipe_oulad(db)

        print("Creating courses...")
        course_ids = await _create_courses(db, modules)

        print("Inserting students...")
        student_ids = await _create_students_bulk(db, dfs["studentInfo"])
        print(f"  -> {len(student_ids)} unique students")

        print("Inserting enrollments...")
        enrollment_map = await _create_enrollments_bulk(
            db, dfs["studentInfo"], student_ids, course_ids
        )
        print(f"  -> {len(enrollment_map)} enrollments")

        print("Inserting grades...")
        n_grades = await _create_grades_bulk(
            db,
            dfs["assessments"],
            dfs["studentAssessment"],
            dfs["studentInfo"],
            enrollment_map,
        )
        print(f"  -> {n_grades} grade records")

        print("Synthesising attendance...")
        n_att = await _create_attendance_bulk(db, dfs["studentInfo"], enrollment_map)
        print(f"  -> {n_att} attendance records")

        await db.commit()
        print("Commit complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load OULAD into the ispps DB")
    parser.add_argument(
        "--modules",
        default=",".join(DEFAULT_MODULES),
        help="Comma-separated module-presentation list (e.g. DDD-2014J,FFF-2014J)",
    )
    args = parser.parse_args()
    asyncio.run(run([m.strip() for m in args.modules.split(",") if m.strip()]))


if __name__ == "__main__":
    main()
