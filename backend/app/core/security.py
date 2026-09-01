"""
Security and Authentication Module
Provides JWT generation, verification, direct bcrypt password hashing, and RBAC guards.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from backend.app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    username: Optional[str] = None
    roles: List[str] = []
    exp: Optional[int] = None


class UserSession(BaseModel):
    user_id: str
    username: str
    roles: List[str]
    is_active: bool = True


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generates a bcrypt hash for a password (truncated to max 72 bytes safely)."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def create_access_token(
    subject: str,
    username: str,
    roles: List[str],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generates a cryptographically signed JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "username": username,
        "roles": roles,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> TokenPayload:
    """Decodes and validates a JWT token signature and expiration."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
        return token_data
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserSession:
    """FastAPI dependency to extract and validate authenticated user session."""
    payload = decode_access_token(token)
    if not payload.sub or not payload.username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload credentials",
        )
    return UserSession(
        user_id=payload.sub,
        username=payload.username,
        roles=payload.roles,
        is_active=True,
    )


def require_roles(allowed_roles: List[str]):
    """Role-Based Access Control (RBAC) dependency factory."""

    async def role_checker(
        current_user: UserSession = Depends(get_current_user),
    ) -> UserSession:
        if not any(role in current_user.roles for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role does not have permission. Required: {allowed_roles}",
            )
        return current_user

    return role_checker
