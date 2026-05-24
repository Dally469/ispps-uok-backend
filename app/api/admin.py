from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password, require_role
from app.deps import auth_school_id, auth_user_id
from app.models import Student, User
from app.schemas import UserCreate, UserUpdate


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
        q = q.where((User.full_name.ilike(term)) | (User.email.ilike(term)))
    if role:
        q = q.where(User.role == role)
    if school_id:
        q = q.where(User.school_id == school_id)

    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    users = result.scalars().all()
    return [_user_to_dict(u) for u in users]


@router.post("/users", status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin")),
):
    """Create a new admin / lecturer / student account.

    For `role == "student"`, also creates the linked Student record using
    the optional `student_number` (required), gender, date_of_birth and
    guardian fields.
    """
    if body.role == "student" and not body.student_number:
        raise HTTPException(
            status_code=422,
            detail="student_number is required when role is 'student'",
        )

    existing = await db.execute(select(User.id).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A user with this email already exists")

    school_id = body.school_id or auth_school_id(auth)

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
        school_id=school_id,
    )
    db.add(user)
    await db.flush()  # populate user.id without committing

    if body.role == "student":
        student = Student(
            user_id=user.id,
            school_id=school_id,
            student_number=body.student_number,
            date_of_birth=body.date_of_birth,
            gender=body.gender,
            guardian_name=body.guardian_name,
            guardian_email=body.guardian_email,
        )
        db.add(student)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        message = str(getattr(exc, "orig", exc)).lower()
        if "student_number" in message:
            raise HTTPException(status_code=409, detail="That student number is already in use")
        if "email" in message:
            raise HTTPException(status_code=409, detail="A user with this email already exists")
        raise HTTPException(status_code=409, detail="Could not create user")

    await db.refresh(user)
    return _user_to_dict(user)


@router.put("/users/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin")),
):
    """Update name, email, school or password. Role is NOT editable here
    (it would leave any linked Student row inconsistent — delete and
    recreate the account instead)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # School scoping: admin can only edit users in their own school
    school_id = auth_school_id(auth)
    if school_id and user.school_id and user.school_id != school_id:
        raise HTTPException(status_code=403, detail="User is in another school")

    update_data = body.model_dump(exclude_unset=True)
    new_password = update_data.pop("password", None)

    if "email" in update_data and update_data["email"] != user.email:
        existing = await db.execute(
            select(User.id).where(User.email == update_data["email"], User.id != user_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="A user with this email already exists")

    for field, value in update_data.items():
        setattr(user, field, value)
    if new_password:
        user.password_hash = hash_password(new_password)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        message = str(getattr(exc, "orig", exc)).lower()
        if "email" in message:
            raise HTTPException(status_code=409, detail="A user with this email already exists")
        raise HTTPException(status_code=409, detail="Could not update user")

    await db.refresh(user)
    return _user_to_dict(user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(require_role("admin")),
):
    if user_id == auth_user_id(auth):
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    school_id = auth_school_id(auth)
    if school_id and user.school_id and user.school_id != school_id:
        raise HTTPException(status_code=403, detail="User is in another school")

    await db.delete(user)
    await db.commit()
    return {"success": True}


def _user_to_dict(u: User) -> dict:
    return {
        "id": str(u.id),
        "full_name": u.full_name,
        "email": u.email,
        "role": u.role,
        "school_id": str(u.school_id) if u.school_id else None,
        "is_active": True,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }
