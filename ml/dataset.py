"""Build the training dataset by querying the live database.

Run via `python -m ml.train` — this module is imported by training/evaluation.
For each enrollment with a 'final' grade, we use everything *except* the
final as input features, and the final grade as the regression target.
"""
from __future__ import annotations

import asyncio
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from app.core.database import async_session
from app.models import Enrollment
from ml.features import FEATURE_NAMES, build_features


PASS_THRESHOLD = 50.0


async def _load_enrollments():
    async with async_session() as db:
        result = await db.execute(
            select(Enrollment).options(
                joinedload(Enrollment.course),
                selectinload(Enrollment.grades),
                selectinload(Enrollment.attendance_records),
            )
        )
        return result.unique().scalars().all()


def _row_from_enrollment(enrollment) -> dict | None:
    finals = [g for g in enrollment.grades if g.assessment_type == "final"]
    if not finals:
        return None
    final = finals[0]
    target = (final.score / final.max_score) * 100.0 if final.max_score else 0.0

    inputs = [g for g in enrollment.grades if g.assessment_type != "final"]
    if not inputs:
        return None

    credit_hours = enrollment.course.credit_hours if enrollment.course else 3
    feats = build_features(inputs, list(enrollment.attendance_records or []), credit_hours)

    row = feats.to_dict()
    row["target_grade"] = round(target, 2)
    row["target_pass"] = int(target >= PASS_THRESHOLD)
    return row


def build_dataframe() -> pd.DataFrame:
    """Materialise the (X, y) training table from the database."""
    enrollments = asyncio.run(_load_enrollments())
    rows = [r for e in enrollments if (r := _row_from_enrollment(e)) is not None]
    if not rows:
        raise RuntimeError(
            "No training rows produced. Make sure the database is seeded "
            "(see db/seed.sql) and enrollments include 'final' grades."
        )
    df = pd.DataFrame(rows)
    return df[FEATURE_NAMES + ["target_grade", "target_pass"]]


def split_xy(df: pd.DataFrame):
    X = df[FEATURE_NAMES].to_numpy()
    y_grade = df["target_grade"].to_numpy()
    y_pass = df["target_pass"].to_numpy()
    return X, y_grade, y_pass
