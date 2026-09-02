"""
Unit Tests for AI Runtime Lifecycle, Auto-Restore, and Readiness Gate (Phases P8 & P9)
"""

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base
from database.models.auth import User
from database.models.runtime_config import SystemRuntimeConfig
from backend.app.services.runtime_service import RuntimeLifecycleService
from backend.app.core.readiness import require_application_ready
from backend.app.core.security import UserSession


@pytest.fixture
async def runtime_test_db():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_full_runtime_readiness_lifecycle(runtime_test_db):
    session = runtime_test_db

    # 1. Fresh database -> NEEDS_BOOTSTRAP
    status1 = await RuntimeLifecycleService.get_readiness_status(session)
    assert status1["is_ready"] is False
    assert status1["status"] == "NEEDS_BOOTSTRAP"

    # 2. Add admin user -> NEEDS_RUNTIME_INIT
    admin = User(
        id="usr-admin-1",
        username="admin_hero",
        email="admin@hero.internal",
        hashed_password="hash",
        role="ADMINISTRATOR",
        is_active=True,
    )
    session.add(admin)
    await session.commit()

    status2 = await RuntimeLifecycleService.get_readiness_status(session)
    assert status2["is_ready"] is False
    assert status2["status"] == "NEEDS_RUNTIME_INIT"

    # 3. Gate should block business access with 503
    mock_user = UserSession(user_id="usr-admin-1", username="admin_hero", roles=["ADMINISTRATOR"])
    with pytest.raises(HTTPException) as exc_info:
        await require_application_ready(db=session, current_user=mock_user)
    assert exc_info.value.status_code == 503

    # 4. Initialize AI Runtime -> READY
    init_res = await RuntimeLifecycleService.initialize_runtime(
        db=session,
        provider="llama_cpp",
        model_id="qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        model_hash="sha256:11223344",
        runtime_profile="BALANCED",
        context_length=8192,
        configured_by="usr-admin-1",
        username="admin_hero",
    )
    assert init_res["status"] == "READY"

    status3 = await RuntimeLifecycleService.get_readiness_status(session)
    assert status3["is_ready"] is True
    assert status3["status"] == "READY"
    assert status3["active_model_id"] == "qwen2.5-coder-7b-instruct-q4_k_m.gguf"

    # Gate should now pass cleanly
    passed = await require_application_ready(db=session, current_user=mock_user)
    assert passed.username == "admin_hero"

    # 5. Subsequent boot: auto restore saved config
    restore_res = await RuntimeLifecycleService.auto_restore_saved_runtime(session)
    assert restore_res["is_restored"] is True
    assert restore_res["model_id"] == "qwen2.5-coder-7b-instruct-q4_k_m.gguf"

    # 6. Trigger Recovery Mode -> RECOVERY_REQUIRED
    rec_res = await RuntimeLifecycleService.trigger_recovery_mode(
        db=session,
        reason="Model weights checksum mismatch detected.",
        username="admin_hero",
    )
    assert rec_res["status"] == "RECOVERY_MODE_ACTIVE"

    status4 = await RuntimeLifecycleService.get_readiness_status(session)
    assert status4["is_ready"] is False
    assert status4["status"] == "RECOVERY_REQUIRED"

    # Gate should now block again
    with pytest.raises(HTTPException) as exc_info2:
        await require_application_ready(db=session, current_user=mock_user)
    assert exc_info2.value.status_code == 503
