import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import get_settings
from app.core.database import get_db
from app.core.email import send_email
from app.core.security import hash_password, require_auth, sign_token, verify_password
from app.models import PasswordResetToken, User
from app.schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    UserOut,
)


router = APIRouter(prefix="/api/auth", tags=["auth"])

RESET_TOKEN_TTL = timedelta(hours=1)


def _user_out(user: User) -> UserOut:
    """Build UserOut with school_name pulled from the eagerly-loaded relationship."""
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        avatar_url=user.avatar_url,
        school_id=user.school_id,
        school_name=user.school.name if user.school else None,
        created_at=user.created_at,
    )


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).options(joinedload(User.school)).where(User.email == body.email)
    )
    user = result.unique().scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = sign_token({
        "userId": str(user.id),
        "email": user.email,
        "role": user.role,
        "schoolId": str(user.school_id) if user.school_id else None,
    })

    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )

    return AuthResponse(token=token, user=_user_out(user))


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("auth_token", path="/")
    return {"success": True}


@router.get("/session", response_model=UserOut)
async def session(
    request: Request,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    result = await db.execute(
        select(User).options(joinedload(User.school)).where(User.id == auth["userId"])
    )
    user = result.unique().scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_out(user)


# ── Forgot / reset password ──────────────────────────────────────────────────

@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Issue a single-use reset token and email it. To avoid leaking
    whether an email is registered, the response is always 200 OK with a
    neutral message — only the side-effect (email) reveals reality."""
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user:
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + RESET_TOKEN_TTL
        db.add(PasswordResetToken(user_id=user.id, token=token, expires_at=expires))
        await db.commit()

        settings = get_settings()
        reset_url = f"{settings.frontend_base_url.rstrip('/')}/reset-password?token={token}"
        body_text = (
            f"Hi {user.full_name},\n\n"
            f"We received a request to reset your ISPPS password.\n"
            f"Open this link within the next hour to choose a new one:\n"
            f"{reset_url}\n\n"
            f"If you didn't request this, ignore this email and your password stays the same.\n\n"
            f"— ISPPS"
        )
        body_html = (
            f"<div style=\"font-family:Inter,Arial,sans-serif;max-width:560px\">"
            f"<p>Hi <b>{user.full_name}</b>,</p>"
            f"<p>We received a request to reset your <b>ISPPS</b> password.</p>"
            f"<p><a href=\"{reset_url}\" "
            f"style=\"display:inline-block;background:#4f46e5;color:#fff;"
            f"padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600\">"
            f"Choose a new password</a></p>"
            f"<p style=\"color:#6b7280;font-size:13px\">"
            f"This link is valid for one hour. If you didn't request it, you can ignore this email.</p>"
            f"<p style=\"color:#9ca3af;font-size:12px\">"
            f"Or paste this URL: <br><code style=\"font-size:11px\">{reset_url}</code></p>"
            f"</div>"
        )
        background_tasks.add_task(
            send_email,
            user.email,
            "[ISPPS] Reset your password",
            body_text,
            body_html,
        )

    return {
        "success": True,
        "message": "If that email is registered, a reset link is on its way.",
    }


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == body.token)
    )
    reset = result.scalar_one_or_none()
    if not reset or reset.used:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has already been used.")
    if reset.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="This reset link has expired. Request a new one.")

    user_result = await db.execute(select(User).where(User.id == reset.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Account no longer exists.")

    user.password_hash = hash_password(body.new_password)
    reset.used = True
    await db.commit()
    return {"success": True, "message": "Password updated. You can sign in now."}
