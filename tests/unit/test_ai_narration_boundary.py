"""
Unit Tests for AI Session Narration Layer Boundary and Provenance (Phase P7)
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base
from database.models.auth import User
from database.models.activity import UserActivityEvent
from database.models.audit import AuditLog
from backend.app.services.activity_service import ActivityService
from backend.app.services.narration_service import SessionNarrationService


@pytest.fixture
async def narration_test_db():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_session_narration_offline_fallback(narration_test_db):
    session = narration_test_db
    session_id = "sess-narrate-999"
    user_id = "usr-eng-002"

    await ActivityService.log_activity(
        db=session,
        session_id=session_id,
        user_id=user_id,
        username="engineer_amit",
        activity_type="PAGE_OPENED",
        page="OPEX_BENCHMARKING",
        plant_id="HARIDWAR",
    )
    await ActivityService.log_activity(
        db=session,
        session_id=session_id,
        user_id=user_id,
        username="engineer_amit",
        activity_type="PLANT_SELECTED",
        page="OPEX_BENCHMARKING",
        plant_id="HARIDWAR",
    )

    # Generate narration with orchestrator=None (Simulating AI offline)
    narration = await SessionNarrationService.generate_narration(
        db=session,
        session_id=session_id,
        orchestrator=None,
    )

    assert narration["session_id"] == session_id
    assert narration["status"] == "AI_UNAVAILABLE_FALLBACK"
    assert narration["source_event_count"] == 2
    assert "engineer_amit" in narration["summary"]
    assert "HARIDWAR" in str(narration["highlights"])
    assert narration["model_id"] == "deterministic-fallback"
