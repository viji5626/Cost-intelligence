"""
Authoritative Audit Trail REST Endpoints
Provides filtered log querying, pagination, and SHA-256 cryptographic chain verification.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.security import UserSession, get_current_user
from backend.app.core.rbac import require_permission, HeroPermission
from backend.app.services.audit_service import AuditService
from database.models.audit import AuditLog

router = APIRouter(prefix="/audit", tags=["Authoritative Audit Trail"])


class AuditLogItemResponse(BaseModel):
    id: str
    sequence_number: Optional[int]
    timestamp: str
    username: str
    role: str
    department: Optional[str]
    scope: Optional[str]
    action: str
    entity_type: str
    entity_id: Optional[str]
    status: str
    session_id: Optional[str]
    client_ip: Optional[str]
    previous_event_hash: str
    event_hash: str
    payload: Dict[str, Any]


class AuditLogListResponse(BaseModel):
    total_count: int
    page: int
    page_size: int
    events: List[AuditLogItemResponse]


@router.get("/logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    action: Optional[str] = Query(None, description="Filter by action name"),
    username: Optional[str] = Query(None, description="Filter by username"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    search: Optional[str] = Query(None, description="Search query across action and entity"),
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(require_permission(HeroPermission.READ_AUDIT.value)),
) -> AuditLogListResponse:
    """Lists audit trail records with server-side filtering, search, and pagination."""
    stmt = select(AuditLog)

    if action:
        stmt = stmt.where(AuditLog.action == action)
    if username:
        stmt = stmt.where(AuditLog.username == username)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if search:
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            (AuditLog.action.ilike(search_pattern))
            | (AuditLog.entity_type.ilike(search_pattern))
            | (AuditLog.username.ilike(search_pattern))
        )

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_stmt)
    total_count = total_res.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    stmt = stmt.order_by(desc(AuditLog.sequence_number)).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    items = [
        AuditLogItemResponse(
            id=row.id,
            sequence_number=row.sequence_number,
            timestamp=row.created_at.isoformat() if row.created_at else datetime.utcnow().isoformat(),
            username=row.username,
            role=row.role,
            department=row.department,
            scope=row.scope,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            status=row.status,
            session_id=row.session_id,
            client_ip=row.client_ip,
            previous_event_hash=row.previous_event_hash or ("0" * 64),
            event_hash=row.event_hash or ("0" * 64),
            payload=row.payload_json or {},
        )
        for row in rows
    ]

    return AuditLogListResponse(
        total_count=total_count,
        page=page,
        page_size=page_size,
        events=items,
    )


@router.get("/verify-integrity")
async def verify_audit_integrity(
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(require_permission(HeroPermission.READ_AUDIT.value)),
) -> Dict[str, Any]:
    """Traverses the full audit trail and validates cryptographic SHA-256 hash chain integrity."""
    return await AuditService.verify_integrity(db)


from fastapi.responses import Response, HTMLResponse
from backend.app.services.audit_export_service import AuditExportService


@router.get("/export/csv")
async def export_audit_csv(
    action: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(require_permission(HeroPermission.EXPORT_AUDIT.value)),
) -> Response:
    """Exports audit trail as RFC 4180 CSV file (Authorized users only)."""
    events = await AuditExportService.get_filtered_events(
        db=db, action=action, username=username, entity_type=entity_type, session_id=session_id, search=search
    )
    csv_data = await AuditExportService.generate_csv(
        db=db, events=events, requesting_user=current_user.username, session_id=session_id
    )

    # Log export audit event
    await AuditService.log_event(
        db=db,
        action="DATA_EXPORTED",
        entity_type="AUDIT_EXPORT",
        entity_id="CSV",
        user_id=current_user.user_id,
        username=current_user.username,
        role=current_user.roles[0] if current_user.roles else "ADMINISTRATOR",
        session_id=current_user.session_id,
        payload_json={"format": "CSV", "record_count": len(events), "session_filter": session_id},
    )

    filename = f"hero_audit_trail_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/xlsx")
async def export_audit_xlsx(
    action: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(require_permission(HeroPermission.EXPORT_AUDIT.value)),
) -> Response:
    """Exports audit trail as formatted Excel (.xlsx) workbook with metadata sheet."""
    events = await AuditExportService.get_filtered_events(
        db=db, action=action, username=username, entity_type=entity_type, session_id=session_id, search=search
    )
    xlsx_bytes = await AuditExportService.generate_xlsx(
        db=db, events=events, requesting_user=current_user.username, session_id=session_id
    )

    await AuditService.log_event(
        db=db,
        action="DATA_EXPORTED",
        entity_type="AUDIT_EXPORT",
        entity_id="XLSX",
        user_id=current_user.user_id,
        username=current_user.username,
        role=current_user.roles[0] if current_user.roles else "ADMINISTRATOR",
        session_id=current_user.session_id,
        payload_json={"format": "XLSX", "record_count": len(events), "session_filter": session_id},
    )

    filename = f"hero_audit_trail_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/pdf")
async def export_audit_pdf(
    action: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(require_permission(HeroPermission.EXPORT_AUDIT.value)),
) -> Response:
    """Exports audit trail as printable PDF report with cryptographic verification footer."""
    events = await AuditExportService.get_filtered_events(
        db=db, action=action, username=username, entity_type=entity_type, session_id=session_id, search=search
    )
    pdf_bytes = await AuditExportService.generate_pdf(
        db=db, events=events, requesting_user=current_user.username, session_id=session_id
    )

    await AuditService.log_event(
        db=db,
        action="DATA_EXPORTED",
        entity_type="AUDIT_EXPORT",
        entity_id="PDF",
        user_id=current_user.user_id,
        username=current_user.username,
        role=current_user.roles[0] if current_user.roles else "ADMINISTRATOR",
        session_id=current_user.session_id,
        payload_json={"format": "PDF", "record_count": len(events), "session_filter": session_id},
    )

    filename = f"hero_audit_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/html", response_class=HTMLResponse)
async def export_audit_offline_html(
    action: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(require_permission(HeroPermission.EXPORT_AUDIT.value)),
) -> HTMLResponse:
    """Exports 100% self-contained, offline Interactive HTML audit trail (zero CDNs/external calls)."""
    events = await AuditExportService.get_filtered_events(
        db=db, action=action, username=username, entity_type=entity_type, session_id=session_id, search=search
    )
    html_content = await AuditExportService.generate_offline_html(
        db=db, events=events, requesting_user=current_user.username, session_id=session_id
    )

    await AuditService.log_event(
        db=db,
        action="DATA_EXPORTED",
        entity_type="AUDIT_EXPORT",
        entity_id="HTML",
        user_id=current_user.user_id,
        username=current_user.username,
        role=current_user.roles[0] if current_user.roles else "ADMINISTRATOR",
        session_id=current_user.session_id,
        payload_json={"format": "OFFLINE_HTML", "record_count": len(events), "session_filter": session_id},
    )

    filename = f"hero_audit_interactive_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.html"
    return HTMLResponse(
        content=html_content,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

