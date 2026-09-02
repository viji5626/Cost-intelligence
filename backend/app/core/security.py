"""
Security and Authentication Module
Provides JWT generation, verification, password hashing, session management, and RBAC guards.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
import re
import uuid
import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from backend.app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    roles: List[str] = []
    plant_scope: List[str] = ["ALL"]
    department: Optional[str] = "ENGINEERING"
    session_id: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None


class UserSession(BaseModel):
    user_id: str
    username: str
    display_name: str = ""
    roles: List[str] = []
    plant_scope: List[str] = ["ALL"]
    department: str = "ENGINEERING"
    session_id: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False


def check_password_complexity(
    password: str,
    min_length: int = 8,
    require_upper: bool = True,
    require_lower: bool = True,
    require_digit: bool = True,
    require_special: bool = True,
) -> Tuple[bool, str]:
    """Validates password against complexity rules."""
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long."
    if require_upper and not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if require_lower and not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter."
    if require_digit and not any(c.isdigit() for c in password):
        return False, "Password must contain at least one numerical digit."
    if require_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character (!@#$%^&*...)."
    return True, "Password meets complexity requirements."


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a stored bcrypt/salted hash."""
    try:
        if hashed_password.startswith("$2a$") or hashed_password.startswith("$2b$") or hashed_password.startswith("$2y$"):
            return bcrypt.checkpw(
                plain_password.encode("utf-8")[:72],
                hashed_password.encode("utf-8"),
            )
        # Fallback for plain bcrypt without prefix variations
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72],
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generates a secure salted bcrypt hash for a password (12 rounds)."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def create_access_token(
    subject: str,
    username: str,
    roles: List[str],
    display_name: str = "",
    plant_scope: Optional[List[str]] = None,
    department: str = "ENGINEERING",
    session_id: Optional[str] = None,
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
        "display_name": display_name or username,
        "roles": roles,
        "plant_scope": plant_scope or ["ALL"],
        "department": department,
        "session_id": session_id or str(uuid.uuid4()),
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


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> UserSession:
    """FastAPI dependency to extract and validate authenticated user session."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if not payload.sub or not payload.username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload credentials",
        )
    return UserSession(
        user_id=payload.sub,
        username=payload.username,
        display_name=payload.display_name or payload.username,
        roles=payload.roles,
        plant_scope=payload.plant_scope,
        department=payload.department or "ENGINEERING",
        session_id=payload.session_id,
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
