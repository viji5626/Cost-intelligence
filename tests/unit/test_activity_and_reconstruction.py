"""
Unit Tests for User Activity Monitoring and Session Reconstruction (Phase P6)
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base
from database.models.auth import User
from database.models.activity import UserActivityEvent
from database.models.audit import AuditLog
from backend.app.services.activity_service import ActivityService
from backend.app.services.audit_service import AuditService


@pytest.fixture
async def activity_test_db():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_session_timeline_reconstruction(activity_test_db):
    session = activity_test_db
    session_id = "sess-recon-test-1234"
    user_id = "usr-eng-001"

    # 1. Log page opened activity
    await ActivityService.log_activity(
        db=session,
        session_id=session_id,
        user_id=user_id,
        username="engineer_vijay",
        activity_type="PAGE_OPENED",
        page="OPEX_BENCHMARKING",
        details_json={"path": "/opex"},
    )

    # 2. Log plant selection
    await ActivityService.log_activity(
        db=session,
        session_id=session_id,
        user_id=user_id,
        username="engineer_vijay",
        activity_type="PLANT_SELECTED",
        page="OPEX_BENCHMARKING",
        plant_id="HARIDWAR",
        details_json={"plant_name": "Haridwar Manufacturing Plant"},
    )

    # 3. Log audit event
    await AuditService.log_event(
        db=session,
        action="OPEX_KPIS_CALCULATED",
        entity_type="PLANT",
        entity_id="HARIDWAR",
        user_id=user_id,
        username="engineer_vijay",
        role="ENGINEERING",
        scope="HARIDWAR",
        session_id=session_id,
        payload_json={"specific_power": 18.4, "status": "CALCULATED"},
    )

    # 4. Reconstruct timeline -> MUST ASSEMBLE ALL 3 CHRONOLOGICALLY
    timeline = await ActivityService.reconstruct_session_timeline(db=session, session_id=session_id)
    assert timeline["session_id"] == session_id
    assert timeline["username"] == "engineer_vijay"
    assert timeline["event_count"] == 3
    assert len(timeline["timeline"]) == 3

    assert timeline["timeline"][0]["activity_type"] == "PAGE_OPENED"
    assert timeline["timeline"][1]["activity_type"] == "PLANT_SELECTED"
    assert timeline["timeline"][2]["activity_type"] == "OPEX_KPIS_CALCULATED"
    assert timeline["timeline"][2]["type"] == "AUDIT_EVENT"
