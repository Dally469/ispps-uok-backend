"""Helper for emitting in-app notifications.

Routers can call `notify(db, recipient_id=..., type=..., title=..., body=...)`
or `notify_many(...)` to fan a single message out to multiple recipients.
The caller is responsible for calling `db.commit()` afterwards.
"""
from __future__ import annotations

import uuid
from typing import Iterable, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification


NotificationType = Literal["prediction", "warning", "grade", "attendance", "system"]


def notify(
    db: AsyncSession,
    *,
    recipient_id: uuid.UUID,
    type: NotificationType,
    title: str,
    body: str,
) -> Notification:
    n = Notification(
        recipient_id=recipient_id,
        type=type,
        title=title[:240],
        body=body,
    )
    db.add(n)
    return n


def notify_many(
    db: AsyncSession,
    *,
    recipient_ids: Iterable[uuid.UUID],
    type: NotificationType,
    title: str,
    body: str,
) -> list[Notification]:
    out: list[Notification] = []
    seen: set[uuid.UUID] = set()
    for rid in recipient_ids:
        if rid is None or rid in seen:
            continue
        seen.add(rid)
        out.append(notify(db, recipient_id=rid, type=type, title=title, body=body))
    return out


async def email_notifications(notification_ids: list[uuid.UUID]) -> None:
    """Look up each notification by id, find its recipient's email, and
    send a formatted message. Designed to be invoked from
    `BackgroundTasks` AFTER the request's db session has been committed,
    so it opens its own short-lived session."""
    if not notification_ids:
        return

    # Lazy imports to keep this module dependency-light.
    from sqlalchemy import select

    from app.core.config import get_settings
    from app.core.database import async_session
    from app.core.email import send_email
    from app.models import User

    settings = get_settings()
    frontend = settings.frontend_base_url.rstrip("/")
    notif_url = f"{frontend}/notifications"

    async with async_session() as db:
        result = await db.execute(
            select(Notification, User)
            .join(User, User.id == Notification.recipient_id)
            .where(Notification.id.in_(notification_ids))
        )
        rows = result.all()

    for note, user in rows:
        if not user.email:
            continue
        subject = f"[ISPPS] {note.title}"
        body_text = (
            f"Hi {user.full_name},\n\n"
            f"{note.body}\n\n"
            f"Open your dashboard: {notif_url}\n\n"
            f"— ISPPS\nIntelligent Student Performance Prediction System"
        )
        body_html = (
            f"<div style=\"font-family:Inter,Arial,sans-serif;max-width:560px\">"
            f"<p>Hi <b>{user.full_name}</b>,</p>"
            f"<p style=\"font-size:15px;line-height:1.5\">{note.body}</p>"
            f"<p><a href=\"{notif_url}\" "
            f"style=\"display:inline-block;background:#4f46e5;color:#fff;"
            f"padding:10px 16px;border-radius:8px;text-decoration:none;font-weight:600\">"
            f"Open ISPPS</a></p>"
            f"<hr style=\"border:none;border-top:1px solid #e5e7eb\">"
            f"<p style=\"color:#9ca3af;font-size:12px\">"
            f"ISPPS · Intelligent Student Performance Prediction System</p>"
            f"</div>"
        )
        await send_email(user.email, subject, body_text, body_html)
