from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import get_db
from app.models import User, Student
from app.schemas import CSVImportRequest
from app.core.security import require_role

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/students")
async def import_students(
    body: CSVImportRequest,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin")),
):
    lines = body.csv_data.strip().split("\n")

    if len(lines) < 2:
        raise HTTPException(status_code=400, detail="CSV must have a header row and at least one data row")

    headers = [h.strip().lower() for h in lines[0].split(",")]
    results = {"imported": 0, "errors": []}

    for i, line in enumerate(lines[1:], start=2):
        values = [v.strip().strip('"') for v in line.split(",")]
        row = {h: (values[idx] if idx < len(values) else "") for idx, h in enumerate(headers)}

        try:
            student_number = row.get("student_number") or row.get("id") or ""
            full_name = row.get("full_name") or row.get("name") or ""
            email = row.get("email", "")
            school_id = row.get("school_id", "")

            if not student_number or not full_name or not school_id:
                results["errors"].append(f"Row {i}: Missing required fields (student_number, full_name, school_id)")
                continue

            user_id = None
            if email:
                stmt = (
                    pg_insert(User)
                    .values(
                        email=email,
                        full_name=full_name,
                        role="student",
                        password_hash="$2b$10$placeholder.import.change.password.000000000000000",
                        school_id=school_id,
                    )
                    .on_conflict_do_update(
                        index_elements=["email"],
                        set_={"full_name": full_name},
                    )
                    .returning(User.id)
                )
                result = await db.execute(stmt)
                user_row = result.fetchone()
                user_id = user_row[0] if user_row else None

            stmt = (
                pg_insert(Student)
                .values(
                    student_number=student_number,
                    school_id=school_id,
                    user_id=user_id,
                    date_of_birth=row.get("date_of_birth") or None,
                    gender=row.get("gender") or None,
                    guardian_name=row.get("guardian_name") or None,
                    guardian_email=row.get("guardian_email") or None,
                )
                .on_conflict_do_update(
                    index_elements=["student_number"],
                    set_={
                        "user_id": user_id,
                        "date_of_birth": row.get("date_of_birth") or None,
                        "gender": row.get("gender") or None,
                        "guardian_name": row.get("guardian_name") or None,
                        "guardian_email": row.get("guardian_email") or None,
                    },
                )
            )
            await db.execute(stmt)
            results["imported"] += 1
        except Exception as e:
            results["errors"].append(f"Row {i}: {str(e)}")

    await db.commit()
    return results
