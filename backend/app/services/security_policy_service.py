"""
Security Policy Service
Retrieves and updates system-wide security policies.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.security_policy import SecurityPolicy


async def get_active_security_policy(db: AsyncSession) -> SecurityPolicy:
    """Retrieves the active system security policy or initializes defaults."""
    res = await db.execute(select(SecurityPolicy))
    policy = res.scalar_one_or_none()
    if not policy:
        policy = SecurityPolicy(
            min_password_length=8,
            require_uppercase=True,
            require_lowercase=True,
            require_digit=True,
            require_special_char=True,
            max_failed_attempts=5,
            lockout_duration_minutes=5,
            session_inactivity_timeout_minutes=480,
            password_expiration_days=0,
        )
        db.add(policy)
        await db.commit()
    return policy
