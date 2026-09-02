"""
Authentication Endpoints
Handles first-boot administrator bootstrap, DB-backed login, session management, and password lifecycle.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.security import (
    UserSession,
    check_password_complexity,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from database.models.auth import User
from database.models.session import UserSession as UserSessionModel
from database.models.audit import AuditLog
from backend.app.services.audit_service import AuditService

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------

class BootstrapStatusResponse(BaseModel):
    is_bootstrapped: bool
    requires_setup: bool
    active_admins: int


class BootstrapAdminRequest(BaseModel):
    username: str
    email: str
    display_name: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    display_name: str
    roles: List[str]
    plant_scope: List[str]
    department: str
    session_id: str
    expires_at: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str


class AvailableUserItem(BaseModel):
    username: str
    display_name: str
    role: str
    department: str
    plant_scope: List[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/bootstrap-status", response_model=BootstrapStatusResponse)
async def get_bootstrap_status(db: AsyncSession = Depends(get_db)) -> BootstrapStatusResponse:
    """Checks if the platform has an active Administrator account configured."""
    result = await db.execute(
        select(func.count(User.id)).where(User.role == "ADMINISTRATOR", User.is_active.is_(True))
    )
    admin_count = result.scalar() or 0
    is_bootstrapped = admin_count > 0
    return BootstrapStatusResponse(
        is_bootstrapped=is_bootstrapped,
        requires_setup=not is_bootstrapped,
        active_admins=admin_count,
    )


@router.get("/available-users", response_model=List[AvailableUserItem])
async def get_available_users(db: AsyncSession = Depends(get_db)) -> List[AvailableUserItem]:
    """Returns active registered users for the authentication username dropdown."""
    result = await db.execute(
        select(User).where(User.is_active.is_(True)).order_by(User.created_at.asc())
    )
    users = result.scalars().all()
    return [
        AvailableUserItem(
            username=u.username,
            display_name=u.display_name,
            role=u.role,
            department=u.department,
            plant_scope=u.plant_scope,
        )
        for u in users
    ]


@router.post("/bootstrap-admin", response_model=TokenResponse)
async def bootstrap_admin(
    request: Request,
    payload: BootstrapAdminRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Creates the initial Administrator account on a clean installation."""
    # Check if already bootstrapped
    status_check = await db.execute(
        select(func.count(User.id)).where(User.role == "ADMINISTRATOR", User.is_active.is_(True))
    )
    admin_count = status_check.scalar() or 0
    if admin_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System is already bootstrapped with an active Administrator account.",
        )

    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    valid, msg = check_password_complexity(payload.password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    now = datetime.now(timezone.utc)
    user_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    hashed_pwd = get_password_hash(payload.password)

    admin_user = User(
        id=user_id,
        username=payload.username.strip(),
        email=payload.email.strip().lower(),
        display_name=payload.display_name.strip(),
        hashed_password=hashed_pwd,
        department="MANAGEMENT",
        plant_scope=["ALL"],
        role="ADMINISTRATOR",
        is_active=True,
        is_superuser=True,
        failed_login_attempts=0,
        password_changed_at=now,
        last_login_at=now,
    )
    db.add(admin_user)

    expires_at = now + timedelta(hours=8)
    user_session = UserSessionModel(
        id=session_id,
        user_id=user_id,
        session_token=session_id,
        client_ip=request.client.host if request.client else "127.0.0.1",
        user_agent=request.headers.get("User-Agent", "Unknown"),
        is_active=True,
        last_activity_at=now,
        expires_at=expires_at,
    )
    await db.commit()

    # Record bootstrap audit event with cryptographic hash chaining
    await AuditService.log_event(
        db=db,
        action="SYSTEM_BOOTSTRAPPED",
        entity_type="SYSTEM",
        entity_id="ROOT",
        user_id=user_id,
        username=admin_user.username,
        role=admin_user.role,
        department=admin_user.department,
        scope="ALL",
        status="SUCCESS",
        session_id=session_id,
        client_ip=request.client.host if request.client else "127.0.0.1",
        payload_json={"message": "First-boot administrator created", "username": admin_user.username},
    )

    token = create_access_token(
        subject=user_id,
        username=admin_user.username,
        display_name=admin_user.display_name,
        roles=[admin_user.role],
        plant_scope=admin_user.plant_scope,
        department=admin_user.department,
        session_id=session_id,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user_id,
        username=admin_user.username,
        display_name=admin_user.display_name,
        roles=[admin_user.role],
        plant_scope=admin_user.plant_scope,
        department=admin_user.department,
        session_id=session_id,
        expires_at=expires_at.isoformat(),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticates users against PostgreSQL, enforces lockout, and issues session JWT."""
    username = credentials.username.strip()
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check account lockout
    if user.locked_until:
        locked_dt = user.locked_until.replace(tzinfo=timezone.utc) if user.locked_until.tzinfo is None else user.locked_until
        if locked_dt > now:
            remaining_seconds = int((locked_dt - now).total_seconds())
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account is temporarily locked due to consecutive failed login attempts. Try again in {remaining_seconds} seconds.",
            )

    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = now + timedelta(minutes=5)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Successful login: reset failed counters
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now

    session_id = str(uuid.uuid4())
    expires_at = now + timedelta(hours=8)

    user_session = UserSessionModel(
        id=session_id,
        user_id=user.id,
        session_token=session_id,
        client_ip=request.client.host if request.client else "127.0.0.1",
        user_agent=request.headers.get("User-Agent", "Unknown"),
        is_active=True,
        last_activity_at=now,
        expires_at=expires_at,
    )
    db.add(user_session)

    # Audit login with hash chaining
    await AuditService.log_event(
        db=db,
        action="AUTH_LOGIN",
        entity_type="AUTH",
        entity_id=user.id,
        user_id=user.id,
        username=user.username,
        role=user.role,
        department=user.department,
        scope=str(user.plant_scope),
        status="SUCCESS",
        session_id=session_id,
        client_ip=request.client.host if request.client else "127.0.0.1",
        payload_json={"login_time": now.isoformat()},
    )

    token = create_access_token(
        subject=user.id,
        username=user.username,
        display_name=user.display_name,
        roles=[user.role],
        plant_scope=user.plant_scope,
        department=user.department,
        session_id=session_id,
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        roles=[user.role],
        plant_scope=user.plant_scope,
        department=user.department,
        session_id=session_id,
        expires_at=expires_at.isoformat(),
    )


@router.get("/me", response_model=UserSession)
@router.get("/session", response_model=UserSession)
async def get_session_profile(
    current_user: UserSession = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserSession:
    """Returns currently authenticated user session, verifying against active database session."""
    if current_user.session_id:
        sess_res = await db.execute(
            select(UserSessionModel).where(
                UserSessionModel.id == current_user.session_id,
                UserSessionModel.is_active.is_(True),
            )
        )
        session_record = sess_res.scalar_one_or_none()
        if not session_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been terminated or expired.",
            )
        now = datetime.now(timezone.utc)
        exp_dt = session_record.expires_at.replace(tzinfo=timezone.utc) if session_record.expires_at.tzinfo is None else session_record.expires_at
        if exp_dt < now:
            session_record.is_active = False
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has expired. Please login again.",
            )
        session_record.last_activity_at = now
        await db.commit()

    return current_user


@router.post("/logout")
async def logout(
    request: Request,
    current_user: UserSession = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Explicitly terminates the user session in database and logs audit event."""
    if current_user.session_id:
        sess_res = await db.execute(
            select(UserSessionModel).where(UserSessionModel.id == current_user.session_id)
        )
        session_record = sess_res.scalar_one_or_none()
        if session_record:
            session_record.is_active = False
            await db.commit()

    await AuditService.log_event(
        db=db,
        action="AUTH_LOGOUT",
        entity_type="AUTH",
        entity_id=current_user.user_id,
        user_id=current_user.user_id,
        username=current_user.username,
        role=current_user.roles[0] if current_user.roles else "VIEWER",
        department=current_user.department,
        scope=str(current_user.plant_scope),
        status="SUCCESS",
        session_id=current_user.session_id,
        client_ip=request.client.host if request.client else "127.0.0.1",
        payload_json={"logout_time": datetime.now(timezone.utc).isoformat()},
    )
    return {"message": "Session terminated successfully."}


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    current_user: UserSession = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates password for the currently authenticated user."""
    if payload.new_password != payload.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New passwords do not match.",
        )

    valid, msg = check_password_complexity(payload.new_password)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    user_res = await db.execute(select(User).where(User.id == current_user.user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    now = datetime.now(timezone.utc)
    user.hashed_password = get_password_hash(payload.new_password)
    user.password_changed_at = now
    await db.commit()

    await AuditService.log_event(
        db=db,
        action="PASSWORD_CHANGED",
        entity_type="USER",
        entity_id=user.id,
        user_id=user.id,
        username=user.username,
        role=user.role,
        department=user.department,
        scope=str(user.plant_scope),
        status="SUCCESS",
        session_id=current_user.session_id,
        payload_json={"changed_at": now.isoformat()},
    )
    return {"message": "Password changed successfully."}
