"""
User Management and Last Administrator Protection Service
"""

from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.auth import User


async def validate_last_admin_guard(
    target_user_id: str,
    action: str,
    db: AsyncSession,
    new_role: Optional[str] = None,
    new_is_active: Optional[bool] = None,
) -> None:
    """
    Enforces that at least one active Administrator must always exist.
    Prevents deleting, deactivating, or demoting the final active Administrator.
    """
    result = await db.execute(select(User).where(User.id == target_user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    is_currently_admin = user.role == "ADMINISTRATOR" and user.is_active

    if not is_currently_admin:
        return

    is_demotion = new_role is not None and new_role != "ADMINISTRATOR"
    is_deactivation = new_is_active is False
    is_deletion = action.upper() == "DELETE"

    if is_demotion or is_deactivation or is_deletion:
        other_admins_res = await db.execute(
            select(func.count(User.id)).where(
                User.role == "ADMINISTRATOR",
                User.is_active.is_(True),
                User.id != target_user_id,
            )
        )
        other_admin_count = other_admins_res.scalar() or 0

        if other_admin_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate, delete, or demote the last remaining active Administrator.",
            )
