"""
Unit Tests for RBAC and Data Scope Enforcement (Phase P3)
"""

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from backend.app.core.security import UserSession
from backend.app.core.rbac import (
    HeroRole,
    HeroPermission,
    ROLE_PERMISSIONS_MAP,
    require_permission,
    require_data_scope,
)


def test_role_permission_hierarchy():
    # Administrator has all permissions
    admin_perms = ROLE_PERMISSIONS_MAP[HeroRole.ADMINISTRATOR.value]
    assert HeroPermission.MANAGE_USERS.value in admin_perms
    assert HeroPermission.MANAGE_RUNTIME.value in admin_perms
    assert HeroPermission.READ_AUDIT.value in admin_perms
    assert HeroPermission.EXPORT_AUDIT.value in admin_perms

    # Central Operations has multi-plant read/run permissions but not user management
    central_perms = ROLE_PERMISSIONS_MAP[HeroRole.CENTRAL_OPERATIONS.value]
    assert HeroPermission.READ_OPEX.value in central_perms
    assert HeroPermission.MANAGE_USERS.value not in central_perms
    assert HeroPermission.MANAGE_RUNTIME.value not in central_perms

    # Viewer has minimal dashboard read permissions
    viewer_perms = ROLE_PERMISSIONS_MAP[HeroRole.VIEWER.value]
    assert HeroPermission.READ_DASHBOARD.value in viewer_perms
    assert HeroPermission.READ_AUDIT.value not in viewer_perms


@pytest.mark.asyncio
async def test_require_permission_guard():
    admin_session = UserSession(
        user_id="usr-admin-1",
        username="admin_user",
        roles=[HeroRole.ADMINISTRATOR.value],
    )
    viewer_session = UserSession(
        user_id="usr-view-1",
        username="viewer_user",
        roles=[HeroRole.VIEWER.value],
    )

    audit_guard = require_permission(HeroPermission.READ_AUDIT.value)

    # Admin should pass
    passed_user = await audit_guard(current_user=admin_session)
    assert passed_user.username == "admin_user"

    # Viewer should be blocked with HTTP 403
    with pytest.raises(HTTPException) as exc_info:
        await audit_guard(current_user=viewer_session)
    assert exc_info.value.status_code == 403
    assert "Permission denied" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_require_data_scope_guard():
    haridwar_user = UserSession(
        user_id="usr-plant-1",
        username="haridwar_head",
        roles=[HeroRole.PLANT_HEAD.value],
        plant_scope=["HARIDWAR"],
    )
    admin_user = UserSession(
        user_id="usr-admin-1",
        username="admin_user",
        roles=[HeroRole.ADMINISTRATOR.value],
        plant_scope=["ALL"],
    )

    scope_checker = require_data_scope(plant_param="plant_id")

    # 1. Haridwar user accessing Haridwar path parameter -> PASS
    req_haridwar = MagicMock()
    req_haridwar.path_params = {"plant_id": "HARIDWAR"}
    req_haridwar.query_params = {}
    res = await scope_checker(request=req_haridwar, current_user=haridwar_user)
    assert res.username == "haridwar_head"

    # 2. Haridwar user accessing Dharuhera -> FAIL with 403
    req_dharuhera = MagicMock()
    req_dharuhera.path_params = {"plant_id": "DHARUHERA"}
    req_dharuhera.query_params = {}
    with pytest.raises(HTTPException) as exc_info:
        await scope_checker(request=req_dharuhera, current_user=haridwar_user)
    assert exc_info.value.status_code == 403
    assert "outside your authorized plant scope" in str(exc_info.value.detail)

    # 3. Administrator accessing Dharuhera -> PASS
    res_admin = await scope_checker(request=req_dharuhera, current_user=admin_user)
    assert res_admin.username == "admin_user"
