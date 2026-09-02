"""
Role-Based Access Control (RBAC) and Data Scope Module
Defines Hero Enterprise Roles, Granular Permissions, and Plant/Department Data Scope Guards.
"""

from enum import Enum
from typing import Callable, List, Optional, Set
from fastapi import Depends, HTTPException, Request, status
from backend.app.core.security import UserSession, get_current_user


class HeroRole(str, Enum):
    ADMINISTRATOR = "ADMINISTRATOR"
    CENTRAL_OPERATIONS = "CENTRAL_OPERATIONS"
    PLANT_HEAD = "PLANT_HEAD"
    PURCHASE = "PURCHASE"
    COMMERCIAL_VAVE = "COMMERCIAL_VAVE"
    ENGINEERING = "ENGINEERING"
    VIEWER = "VIEWER"


class HeroPermission(str, Enum):
    MANAGE_USERS = "MANAGE_USERS"
    MANAGE_SYSTEM_SETTINGS = "MANAGE_SYSTEM_SETTINGS"
    MANAGE_RUNTIME = "MANAGE_RUNTIME"
    MANAGE_MODELS = "MANAGE_MODELS"
    MANAGE_PROVIDERS = "MANAGE_PROVIDERS"
    READ_AUDIT = "READ_AUDIT"
    EXPORT_AUDIT = "EXPORT_AUDIT"
    READ_USER_ACTIVITY = "READ_USER_ACTIVITY"
    READ_DASHBOARD = "READ_DASHBOARD"
    READ_OPEX = "READ_OPEX"
    READ_IDEATHON = "READ_IDEATHON"
    READ_OPPORTUNITY = "READ_OPPORTUNITY"
    READ_GOVERNANCE = "READ_GOVERNANCE"
    INGEST_DATA = "INGEST_DATA"
    EXPORT_DATA = "EXPORT_DATA"
    RUN_ANALYSIS = "RUN_ANALYSIS"
    RUN_AI = "RUN_AI"
    READ_ENGINEERING_EVIDENCE = "READ_ENGINEERING_EVIDENCE"


ROLE_PERMISSIONS_MAP: dict[str, Set[str]] = {
    HeroRole.ADMINISTRATOR.value: {
        HeroPermission.MANAGE_USERS.value,
        HeroPermission.MANAGE_SYSTEM_SETTINGS.value,
        HeroPermission.MANAGE_RUNTIME.value,
        HeroPermission.MANAGE_MODELS.value,
        HeroPermission.MANAGE_PROVIDERS.value,
        HeroPermission.READ_AUDIT.value,
        HeroPermission.EXPORT_AUDIT.value,
        HeroPermission.READ_USER_ACTIVITY.value,
        HeroPermission.READ_DASHBOARD.value,
        HeroPermission.READ_OPEX.value,
        HeroPermission.READ_IDEATHON.value,
        HeroPermission.READ_OPPORTUNITY.value,
        HeroPermission.READ_GOVERNANCE.value,
        HeroPermission.INGEST_DATA.value,
        HeroPermission.EXPORT_DATA.value,
        HeroPermission.RUN_ANALYSIS.value,
        HeroPermission.RUN_AI.value,
        HeroPermission.READ_ENGINEERING_EVIDENCE.value,
    },
    HeroRole.CENTRAL_OPERATIONS.value: {
        HeroPermission.READ_DASHBOARD.value,
        HeroPermission.READ_OPEX.value,
        HeroPermission.READ_IDEATHON.value,
        HeroPermission.READ_OPPORTUNITY.value,
        HeroPermission.READ_GOVERNANCE.value,
        HeroPermission.INGEST_DATA.value,
        HeroPermission.EXPORT_DATA.value,
        HeroPermission.RUN_ANALYSIS.value,
        HeroPermission.RUN_AI.value,
        HeroPermission.READ_USER_ACTIVITY.value,
    },
    HeroRole.PLANT_HEAD.value: {
        HeroPermission.READ_DASHBOARD.value,
        HeroPermission.READ_OPEX.value,
        HeroPermission.READ_IDEATHON.value,
        HeroPermission.READ_OPPORTUNITY.value,
        HeroPermission.RUN_ANALYSIS.value,
        HeroPermission.RUN_AI.value,
    },
    HeroRole.PURCHASE.value: {
        HeroPermission.READ_DASHBOARD.value,
        HeroPermission.READ_OPPORTUNITY.value,
        HeroPermission.READ_IDEATHON.value,
        HeroPermission.RUN_ANALYSIS.value,
        HeroPermission.RUN_AI.value,
        HeroPermission.EXPORT_DATA.value,
    },
    HeroRole.COMMERCIAL_VAVE.value: {
        HeroPermission.READ_DASHBOARD.value,
        HeroPermission.READ_IDEATHON.value,
        HeroPermission.READ_ENGINEERING_EVIDENCE.value,
        HeroPermission.READ_OPPORTUNITY.value,
        HeroPermission.READ_GOVERNANCE.value,
        HeroPermission.RUN_ANALYSIS.value,
        HeroPermission.RUN_AI.value,
    },
    HeroRole.ENGINEERING.value: {
        HeroPermission.READ_DASHBOARD.value,
        HeroPermission.READ_IDEATHON.value,
        HeroPermission.READ_ENGINEERING_EVIDENCE.value,
        HeroPermission.RUN_AI.value,
    },
    HeroRole.VIEWER.value: {
        HeroPermission.READ_DASHBOARD.value,
        HeroPermission.RUN_AI.value,
    },
    # Backward compatibility aliases
    "ADMIN": {
        HeroPermission.MANAGE_USERS.value,
        HeroPermission.MANAGE_SYSTEM_SETTINGS.value,
        HeroPermission.MANAGE_RUNTIME.value,
        HeroPermission.MANAGE_MODELS.value,
        HeroPermission.MANAGE_PROVIDERS.value,
        HeroPermission.READ_AUDIT.value,
        HeroPermission.EXPORT_AUDIT.value,
        HeroPermission.READ_USER_ACTIVITY.value,
        HeroPermission.READ_DASHBOARD.value,
        HeroPermission.READ_OPEX.value,
        HeroPermission.READ_IDEATHON.value,
        HeroPermission.READ_OPPORTUNITY.value,
        HeroPermission.READ_GOVERNANCE.value,
        HeroPermission.INGEST_DATA.value,
        HeroPermission.EXPORT_DATA.value,
        HeroPermission.RUN_ANALYSIS.value,
        HeroPermission.RUN_AI.value,
        HeroPermission.READ_ENGINEERING_EVIDENCE.value,
    },
    "ENGINEER": {
        HeroPermission.READ_DASHBOARD.value,
        HeroPermission.READ_IDEATHON.value,
        HeroPermission.READ_ENGINEERING_EVIDENCE.value,
        HeroPermission.RUN_AI.value,
    },
    "PLANT_MANAGER": {
        HeroPermission.READ_DASHBOARD.value,
        HeroPermission.READ_OPEX.value,
        HeroPermission.READ_IDEATHON.value,
        HeroPermission.READ_OPPORTUNITY.value,
        HeroPermission.RUN_ANALYSIS.value,
        HeroPermission.RUN_AI.value,
    },
    "EXECUTIVE": {
        HeroPermission.READ_DASHBOARD.value,
        HeroPermission.RUN_AI.value,
    },
}


def require_permission(required_permission: str) -> Callable:
    """FastAPI dependency to verify if user's roles grant the required permission."""

    async def permission_checker(
        current_user: UserSession = Depends(get_current_user),
    ) -> UserSession:
        user_permissions: Set[str] = set()
        for role in current_user.roles:
            user_permissions.update(ROLE_PERMISSIONS_MAP.get(role, set()))

        if required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required permission '{required_permission}' is not granted to roles {current_user.roles}.",
            )
        return current_user

    return permission_checker


def require_data_scope(plant_param: str = "plant_id") -> Callable:
    """FastAPI dependency to enforce plant-level data scope isolation."""

    async def data_scope_checker(
        request: Request,
        current_user: UserSession = Depends(get_current_user),
    ) -> UserSession:
        # Administrators and Central Operations have universal plant visibility
        if any(r in [HeroRole.ADMINISTRATOR.value, HeroRole.CENTRAL_OPERATIONS.value, "ADMIN"] for r in current_user.roles):
            return current_user

        if "ALL" in current_user.plant_scope:
            return current_user

        # Extract plant_id from path parameters or query parameters
        requested_plant = request.path_params.get(plant_param) or request.query_params.get(plant_param)

        if requested_plant:
            normalized_plant = requested_plant.upper().strip()
            user_plants = [p.upper().strip() for p in current_user.plant_scope]
            if normalized_plant not in user_plants:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Plant '{requested_plant}' is outside your authorized plant scope {current_user.plant_scope}.",
                )

        return current_user

    return data_scope_checker
