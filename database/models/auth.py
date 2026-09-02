"""
Authentication and Role Models
"""

from datetime import datetime, timezone
from typing import Optional, List
import uuid
from sqlalchemy import Boolean, String, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from database.models.base import BaseModel


class User(BaseModel):
    """User account model for enterprise RBAC and data scope authentication."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    department: Mapped[str] = mapped_column(String(100), nullable=False, default="ENGINEERING")
    plant_scope: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=lambda: ["ALL"])
    role: Mapped[str] = mapped_column(String(50), default="VIEWER", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __init__(self, **kwargs):
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        if "is_active" not in kwargs:
            kwargs["is_active"] = True
        if "is_superuser" not in kwargs:
            kwargs["is_superuser"] = False
        if "failed_login_attempts" not in kwargs:
            kwargs["failed_login_attempts"] = 0
        if "plant_scope" not in kwargs:
            kwargs["plant_scope"] = ["ALL"]
        if "department" not in kwargs:
            kwargs["department"] = "ENGINEERING"
        if "display_name" not in kwargs:
            kwargs["display_name"] = kwargs.get("full_name") or kwargs.get("username", "")
        if "password_changed_at" not in kwargs:
            kwargs["password_changed_at"] = datetime.now(timezone.utc)
        if "created_at" not in kwargs:
            kwargs["created_at"] = datetime.now(timezone.utc)
        if "updated_at" not in kwargs:
            kwargs["updated_at"] = datetime.now(timezone.utc)
        super().__init__(**kwargs)
