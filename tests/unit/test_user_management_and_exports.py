"""
Unit Tests for User Management and Multi-Format Audit Exports (Phases P10 & P11)
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base
from database.models.auth import User
from database.models.audit import AuditLog
from backend.app.services.audit_service import AuditService
from backend.app.services.audit_export_service import AuditExportService


@pytest.fixture
async def export_test_db():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_multi_format_audit_exports(export_test_db):
    session = export_test_db

    # Seed 3 audit events
    await AuditService.log_event(
        db=session,
        action="USER_CREATED",
        entity_type="USER",
        entity_id="usr-1",
        username="admin_hero",
        role="ADMINISTRATOR",
        payload_json={"target": "plant_head_haridwar"},
    )
    await AuditService.log_event(
        db=session,
        action="OPEX_BENCHMARK_COMPARED",
        entity_type="PLANT",
        entity_id="HARIDWAR",
        username="plant_head_haridwar",
        role="PLANT_HEAD",
        payload_json={"specific_power_var": 0.12},
    )

    events = await AuditExportService.get_filtered_events(db=session)
    assert len(events) >= 2

    # 1. Test CSV Export
    csv_data = await AuditExportService.generate_csv(db=session, events=events, requesting_user="admin_hero")
    assert "Sequence Number,Timestamp (UTC)" in csv_data
    assert "USER_CREATED" in csv_data
    assert "plant_head_haridwar" in csv_data

    # 2. Test Excel (.xlsx) Export
    xlsx_bytes = await AuditExportService.generate_xlsx(db=session, events=events, requesting_user="admin_hero")
    assert len(xlsx_bytes) > 1000
    assert xlsx_bytes.startswith(b"PK")  # Standard zip/xlsx header

    # 3. Test PDF Export
    pdf_bytes = await AuditExportService.generate_pdf(db=session, events=events, requesting_user="admin_hero")
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")

    # 4. Test Offline Interactive HTML Export
    html_str = await AuditExportService.generate_offline_html(db=session, events=events, requesting_user="admin_hero")
    assert "<!DOCTYPE html>" in html_str
    assert "HERO COST INTELLIGENCE PLATFORM" in html_str
    assert "USER_CREATED" in html_str
    assert "default-src 'none'" in html_str  # Content security policy

    # Verify zero external CDN / remote URLs in offline HTML
    assert "http://" not in html_str
    assert "https://" not in html_str
    assert "googleapis.com" not in html_str
    assert "cdnjs.cloudflare.com" not in html_str
