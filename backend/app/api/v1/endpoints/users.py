"""
User Management REST Endpoints
Provides administrator CRUD operations, account unlocking, role & plant scope assignment, and last-admin protection.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.security import (
    UserSession,
    check_password_complexity,
    get_password_hash,
)
from backend.app.core.rbac import require_permission, HeroPermission
from backend.app.services.user_service import validate_last_admin_guard
from backend.app.services.audit_service import AuditService
from database.models.auth import User

router = APIRouter(prefix="/users", tags=["User & Access Management"])


class UserItemResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: str
    department: str
    plant_scope: List[str]
    role: str
    is_active: bool
    is_superuser: bool
    failed_login_attempts: int
    is_locked: bool
    last_login_at: Optional[str]
    created_at: str


class UserListResponse(BaseModel):
    total_count: int
    page: int
    page_size: int
    users: List[UserItemResponse]


class CreateUserRequest(BaseModel):
    username: str
    email: str
    display_name: str
    department: str = "ENGINEERING"
    plant_scope: List[str] = ["ALL"]
    role: str = "VIEWER"
    password: str


class UpdateUserRequest(BaseModel):
    display_name: Optional[str] = None
    department: Optional[str] = None
    plant_scope: Optional[List[str]] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(require_permission(HeroPermission.MANAGE_USERS.value)),
) -> UserListResponse:
    """Lists all user accounts with pagination and role filtering (Administrator only)."""
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    if search:
        p = f"%{search.strip()}%"
        stmt = stmt.where((User.username.ilike(p)) | (User.display_name.ilike(p)) | (User.email.ilike(p)))

    count_res = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total_count = count_res.scalar() or 0

    offset = (page - 1) * page_size
    stmt = stmt.order_by(desc(User.created_at)).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    users = result.scalars().all()

    now = datetime.now(timezone.utc)
    items = []
    for u in users:
        is_locked = bool(u.locked_until and (u.locked_until.replace(tzinfo=timezone.utc) if u.locked_until.tzinfo is None else u.locked_until) > now)
        items.append(
            UserItemResponse(
                id=u.id,
                username=u.username,
                email=u.email,
                display_name=u.display_name,
                department=u.department,
                plant_scope=u.plant_scope or ["ALL"],
                role=u.role,
                is_active=u.is_active,
                is_superuser=u.is_superuser,
                failed_login_attempts=u.failed_login_attempts,
                is_locked=is_locked,
                last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
                created_at=u.created_at.isoformat() if u.created_at else now.isoformat(),
            )
        )

    return UserListResponse(
        total_count=total_count,
        page=page,
        page_size=page_size,
        users=items,
    )


@router.post("", response_model=UserItemResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: CreateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(require_permission(HeroPermission.MANAGE_USERS.value)),
) -> UserItemResponse:
    """Creates a new user account with role and plant scope assignment (Administrator only)."""
    # Check duplicate
    existing = await db.execute(
        select(User).where((User.username == payload.username.strip()) | (User.email == payload.email.strip().lower()))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username or email already exists.")

    valid, msg = check_password_complexity(payload.password)
    if not valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    now = datetime.now(timezone.utc)
    new_user = User(
        id=str(uuid.uuid4()),
        username=payload.username.strip(),
        email=payload.email.strip().lower(),
        display_name=payload.display_name.strip(),
        department=payload.department,
        plant_scope=payload.plant_scope,
        role=payload.role,
        hashed_password=get_password_hash(payload.password),
        is_active=True,
        is_superuser=payload.role == "ADMINISTRATOR",
        failed_login_attempts=0,
        password_changed_at=now,
    )
    db.add(new_user)

    await AuditService.log_event(
        db=db,
        action="USER_CREATED",
        entity_type="USER",
        entity_id=new_user.id,
        user_id=current_user.user_id,
        username=current_user.username,
        role=current_user.roles[0] if current_user.roles else "ADMINISTRATOR",
        payload_json={"username": new_user.username, "role": new_user.role, "plant_scope": new_user.plant_scope},
    )
    await db.commit()

    return UserItemResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        display_name=new_user.display_name,
        department=new_user.department,
        plant_scope=new_user.plant_scope,
        role=new_user.role,
        is_active=new_user.is_active,
        is_superuser=new_user.is_superuser,
        failed_login_attempts=0,
        is_locked=False,
        last_login_at=None,
        created_at=now.isoformat(),
    )


@router.put("/{user_id}", response_model=UserItemResponse)
async def update_user(
    user_id: str,
    payload: UpdateUserRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(require_permission(HeroPermission.MANAGE_USERS.value)),
) -> UserItemResponse:
    """Updates user profile, role, or active status with last-admin protection (Administrator only)."""
    # Guard against deleting/demoting/deactivating last admin
    await validate_last_admin_guard(
        target_user_id=user_id,
        action="UPDATE",
        db=db,
        new_role=payload.role,
        new_is_active=payload.is_active,
    )

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if payload.display_name is not None:
        user.display_name = payload.display_name.strip()
    if payload.department is not None:
        user.department = payload.department
    if payload.plant_scope is not None:
        user.plant_scope = payload.plant_scope
    if payload.role is not None:
        user.role = payload.role
        user.is_superuser = payload.role == "ADMINISTRATOR"
    if payload.is_active is not None:
        user.is_active = payload.is_active

    await AuditService.log_event(
        db=db,
        action="USER_UPDATED",
        entity_type="USER",
        entity_id=user.id,
        user_id=current_user.user_id,
        username=current_user.username,
        role=current_user.roles[0] if current_user.roles else "ADMINISTRATOR",
        payload_json={"username": user.username, "updated_fields": payload.model_dump(exclude_unset=True)},
    )
    await db.commit()

    now = datetime.now(timezone.utc)
    is_locked = bool(user.locked_until and (user.locked_until.replace(tzinfo=timezone.utc) if user.locked_until.tzinfo is None else user.locked_until) > now)

    return UserItemResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        department=user.department,
        plant_scope=user.plant_scope,
        role=user.role,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        failed_login_attempts=user.failed_login_attempts,
        is_locked=is_locked,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat() if user.created_at else now.isoformat(),
    )


@router.post("/{user_id}/unlock")
async def unlock_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(require_permission(HeroPermission.MANAGE_USERS.value)),
):
    """Unlocks a temporarily locked user account (Administrator only)."""
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.failed_login_attempts = 0
    user.locked_until = None

    await AuditService.log_event(
        db=db,
        action="USER_UNLOCKED",
        entity_type="USER",
        entity_id=user.id,
        user_id=current_user.user_id,
        username=current_user.username,
        role=current_user.roles[0] if current_user.roles else "ADMINISTRATOR",
        payload_json={"unlocked_username": user.username},
    )
    await db.commit()
    return {"message": f"User '{user.username}' successfully unlocked."}
