"""
Authentication Endpoints
Handles local synthetic user authentication and JWT session token generation.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from backend.app.core.security import (
    UserSession,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication & RBAC"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    roles: List[str]


# Synthetic demo users for Phase 0 offline validation
SYNTHETIC_USERS = {
    "admin": {
        "user_id": "usr-0000-admin",
        "username": "admin",
        "password": "hero_admin_password",
        "roles": ["ADMIN", "ENGINEER", "EXECUTIVE"],
    },
    "engineer": {
        "user_id": "usr-0001-eng",
        "username": "engineer",
        "password": "hero_eng_password",
        "roles": ["ENGINEER"],
    },
    "plant_manager": {
        "user_id": "usr-0002-plant",
        "username": "plant_manager",
        "password": "hero_plant_password",
        "roles": ["PLANT_MANAGER"],
    },
}


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest) -> TokenResponse:
    """Synthetic local authentication endpoint for offline development."""
    user = SYNTHETIC_USERS.get(credentials.username)
    if not user or user["password"] != credentials.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid synthetic credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        subject=user["user_id"],
        username=user["username"],
        roles=user["roles"],
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user["user_id"],
        username=user["username"],
        roles=user["roles"],
    )


@router.get("/me", response_model=UserSession)
async def get_profile(
    current_user: UserSession = Depends(get_current_user),
) -> UserSession:
    """Returns currently authenticated user session and assigned RBAC roles."""
    return current_user
