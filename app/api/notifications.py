from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_auth
from app.deps import auth_user_id
from app.models import Notification


router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ── Schemas (kept local — not reused elsewhere) ──────────────────────────────

class NotificationOut(BaseModel):
    id: str
    recipient_id: str
    type: str
    title: str
    body: str
    is_read: bool
    created_at: str | None


def _format(n: Notification) -> dict:
    return {
        "id": str(n.id),
        "recipient_id": str(n.recipient_id),
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
async def list_my_notifications(
    is_read: bool | None = None,
    type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    user_id = auth_user_id(auth)
    q = (
        select(Notification)
        .where(Notification.recipient_id == user_id)
        .order_by(Notification.created_at.desc())
    )
    if is_read is not None:
        q = q.where(Notification.is_read == is_read)
    if type:
        q = q.where(Notification.type == type)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return [_format(n) for n in result.scalars().all()]


@router.get("/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    user_id = auth_user_id(auth)
    result = await db.execute(
        select(Notification.id).where(
            Notification.recipient_id == user_id,
            Notification.is_read == False,  # noqa: E712
        )
    )
    return {"count": len(result.scalars().all())}


@router.put("/{notification_id}/read")
async def mark_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    user_id = auth_user_id(auth)
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    if n.recipient_id != user_id:
        raise HTTPException(status_code=403, detail="Not your notification")
    n.is_read = True
    await db.commit()
    return _format(n)


@router.put("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    user_id = auth_user_id(auth)
    await db.execute(
        update(Notification)
        .where(Notification.recipient_id == user_id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    await db.commit()
    return {"success": True}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    user_id = auth_user_id(auth)
    result = await db.execute(select(Notification).where(Notification.id == notification_id))
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    if n.recipient_id != user_id:
        raise HTTPException(status_code=403, detail="Not your notification")
    await db.delete(n)
    await db.commit()
    return {"success": True}
