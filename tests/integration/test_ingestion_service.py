"""
Integration Tests for Master Ingestion Service
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base
from backend.app.services.ingestion.ingestion_service import IngestionService
from backend.app.services.ingestion.models import IngestionTarget
from database.models.audit import AuditLog
from database.models.plant_opex import OpexRecord, Plant


@pytest.fixture
async def ingestion_test_session():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        # Seed test plant
        plant = Plant(id="plt-01", plant_code="PLANT-HAR", name="Haridwar Plant", location="Haridwar", state="UK")
        session.add(plant)
        await session.commit()
        yield session

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_ingest_plant_opex_csv_live_and_audit(ingestion_test_session: AsyncSession):
    session = ingestion_test_session

    csv_data = (
        "plant_code,period,production_quantity,electricity_kwh,total_opex\n"
        "PLANT-HAR,2024-04-01,150000,3300000,75000000\n"
        "PLANT-HAR,2024-05-01,160000,3500000,80000000\n"
    ).encode("utf-8")

    summary = await IngestionService.process_file_bytes(
        session=session,
        file_bytes=csv_data,
        filename="hero_opex_q1.csv",
        target=IngestionTarget.PLANT_OPEX,
        user_id="usr-test-admin",
        dry_run=False,
    )

    assert summary.status == "COMPLETED"
    assert summary.total_rows == 2
    assert summary.valid_rows == 2
    assert summary.rejected_rows == 0
    assert summary.file_hash is not None

    # Verify records persisted in database
    records = (await session.execute(select(OpexRecord))).scalars().all()
    assert len(records) == 2

    # Verify audit log entry created
    audit_logs = (await session.execute(select(AuditLog).where(AuditLog.action == "INGESTION_BATCH"))).scalars().all()
    assert len(audit_logs) >= 1
    assert audit_logs[0].entity_type == "PLANT_OPEX"
