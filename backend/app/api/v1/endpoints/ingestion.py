"""
File Ingestion and Data Staging API Endpoints
"""

from typing import Dict, List
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.security import UserSession, get_current_user
from backend.app.services.ingestion.ingestion_service import IngestionService
from backend.app.services.ingestion.models import (
    COLUMN_ALIASES,
    IngestionBatchSummary,
    IngestionTarget,
)

router = APIRouter(prefix="/ingestion", tags=["Data Ingestion & Staging"])


@router.post("/upload", response_model=IngestionBatchSummary, status_code=status.HTTP_200_OK)
async def upload_and_process_file(
    file: UploadFile = File(...),
    target: IngestionTarget = Form(...),
    dry_run: bool = Form(False),
    allow_unusual_data: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> IngestionBatchSummary:
    """
    Uploads an Excel or CSV spreadsheet, validates headers and rows, detects anomalies,
    and commits valid records to the database (or dry-run previews without saving).
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    try:
        summary = await IngestionService.process_file_bytes(
            session=db,
            file_bytes=file_bytes,
            filename=file.filename,
            target=target,
            user_id=current_user.user_id,
            dry_run=dry_run,
            allow_unusual_data=allow_unusual_data,
        )
        return summary
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process ingestion file: {str(exc)}",
        ) from exc


@router.get("/templates/{target}", response_model=Dict[str, List[str]])
async def get_target_schema_template(
    target: IngestionTarget,
    current_user: UserSession = Depends(get_current_user),
) -> Dict[str, List[str]]:
    """Returns canonical field names and recognized column aliases for the given ingestion target."""
    return COLUMN_ALIASES.get(target, {})
