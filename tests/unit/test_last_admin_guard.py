"""
Unit Tests for Last Administrator Protection Guard (Phase P4)
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base
from database.models.auth import User
from backend.app.services.user_service import validate_last_admin_guard


@pytest.fixture
async def test_session():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_single_admin_demotion_blocked(test_session):
    admin = User(
        id="admin-01",
        username="sole_admin",
        email="admin@hero.internal",
        hashed_password="hashed_dummy_password",
        role="ADMINISTRATOR",
        is_active=True,
    )
    test_session.add(admin)
    await test_session.commit()

    # Attempt to demote sole admin to VIEWER -> Must raise 400
    with pytest.raises(HTTPException) as exc_info:
        await validate_last_admin_guard(
            target_user_id="admin-01",
            action="UPDATE",
            db=test_session,
            new_role="VIEWER",
        )
    assert exc_info.value.status_code == 400
    assert "last remaining active Administrator" in str(exc_info.value.detail)

    # Attempt to deactivate sole admin -> Must raise 400
    with pytest.raises(HTTPException) as exc_info:
        await validate_last_admin_guard(
            target_user_id="admin-01",
            action="UPDATE",
            db=test_session,
            new_is_active=False,
        )
    assert exc_info.value.status_code == 400

    # Attempt to delete sole admin -> Must raise 400
    with pytest.raises(HTTPException) as exc_info:
        await validate_last_admin_guard(
            target_user_id="admin-01",
            action="DELETE",
            db=test_session,
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_multiple_admins_allows_modification(test_session):
    admin1 = User(
        id="admin-01",
        username="admin_one",
        email="admin1@hero.internal",
        hashed_password="hashed_dummy_password",
        role="ADMINISTRATOR",
        is_active=True,
    )
    admin2 = User(
        id="admin-02",
        username="admin_two",
        email="admin2@hero.internal",
        hashed_password="hashed_dummy_password",
        role="ADMINISTRATOR",
        is_active=True,
    )
    test_session.add_all([admin1, admin2])
    await test_session.commit()

    # Deactivating admin1 when admin2 exists is permitted (no exception raised)
    await validate_last_admin_guard(
        target_user_id="admin-01",
        action="UPDATE",
        db=test_session,
        new_is_active=False,
    )
