"""
Unit Tests for Authoritative Audit Trail and SHA-256 Hash Chaining (Phase P5)
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base
from database.models.audit import AuditLog
from backend.app.services.audit_service import AuditService


@pytest.fixture
async def audit_test_db():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_audit_log_sequential_chain_and_verification(audit_test_db):
    session = audit_test_db

    # 1. Log three sequential events
    ev1 = await AuditService.log_event(
        db=session,
        action="USER_CREATED",
        entity_type="USER",
        entity_id="usr-100",
        username="admin_hero",
        role="ADMINISTRATOR",
        payload_json={"username": "engineer_1", "role": "ENGINEERING"},
    )
    assert ev1.sequence_number == 1
    assert ev1.previous_event_hash == "0" * 64
    assert ev1.event_hash.startswith("sha256:")

    ev2 = await AuditService.log_event(
        db=session,
        action="PLANT_BENCHMARKED",
        entity_type="PLANT",
        entity_id="HARIDWAR",
        username="engineer_1",
        role="ENGINEERING",
        payload_json={"specific_power_variance": 0.42},
    )
    assert ev2.sequence_number == 2
    assert ev2.previous_event_hash == ev1.event_hash
    assert ev2.event_hash.startswith("sha256:")

    ev3 = await AuditService.log_event(
        db=session,
        action="IDEA_REVIEWED",
        entity_type="IDEA",
        entity_id="idea-999",
        username="admin_hero",
        role="ADMINISTRATOR",
        payload_json={"decision": "APPROVED", "net_saving": 4500000},
    )
    assert ev3.sequence_number == 3
    assert ev3.previous_event_hash == ev2.event_hash

    # 2. Verify audit integrity -> MUST BE INTACT
    integrity = await AuditService.verify_integrity(session)
    assert integrity["is_valid"] is True
    assert integrity["total_events_checked"] == 3
    assert integrity["chain_status"] == "INTACT"


@pytest.mark.asyncio
async def test_audit_tamper_detection(audit_test_db):
    session = audit_test_db

    ev1 = await AuditService.log_event(
        db=session,
        action="EVENT_1",
        entity_type="SYSTEM",
        payload_json={"data": 1},
    )
    ev2 = await AuditService.log_event(
        db=session,
        action="EVENT_2",
        entity_type="SYSTEM",
        payload_json={"data": 2},
    )

    # Tamper with event 1's payload directly
    ev1.payload_json = {"data": 999999}  # altered data without recomputing hash
    await session.commit()

    # Verify integrity -> MUST FAIL AND CATCH SEQUENCE 1
    integrity = await AuditService.verify_integrity(session)
    assert integrity["is_valid"] is False
    assert integrity["chain_status"] == "TAMPERED"
    assert integrity["corrupted_at_sequence"] == 1


@pytest.mark.asyncio
async def test_audit_secret_redaction(audit_test_db):
    session = audit_test_db

    ev = await AuditService.log_event(
        db=session,
        action="AUTH_LOGIN",
        entity_type="AUTH",
        payload_json={
            "username": "admin",
            "password": "SuperSecretPassword123!",
            "access_token": "secret_jwt_token_payload",
            "safe_metadata": "Hero Plant Haridwar",
        },
    )
    assert ev.payload_json["password"] == "[REDACTED]"
    assert ev.payload_json["access_token"] == "[REDACTED]"
    assert ev.payload_json["safe_metadata"] == "Hero Plant Haridwar"
