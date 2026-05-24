from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User
from app.core.security import require_role

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def list_users(
    search: str | None = None,
    role: str | None = None,
    school_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin")),
):
    q = select(User).order_by(User.created_at.desc())
    if search:
        term = f"%{search}%"
        q = q.where(
            (User.full_name.ilike(term)) | (User.email.ilike(term))
        )
    if role:
        q = q.where(User.role == role)
    if school_id:
        q = q.where(User.school_id == school_id)

    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role,
            "school_id": str(u.school_id) if u.school_id else None,
            "is_active": True,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]
