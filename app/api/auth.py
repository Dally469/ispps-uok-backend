from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models import User
from app.schemas import LoginRequest, UserOut, AuthResponse
from app.core.security import verify_password, sign_token, require_auth

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

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

    return AuthResponse(
        token=token,
        user=UserOut.model_validate(user),
    )


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
    result = await db.execute(select(User).where(User.id == auth["userId"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user)
