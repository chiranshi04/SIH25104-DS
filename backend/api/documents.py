"""Admin document storage API; AI ingestion remains a Phase 11 boundary."""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth.dependencies import require_roles
from backend.config import settings
from backend.database.connection import get_db
from backend.database.document_schemas import DocumentDeleteResponse, DocumentResponse
from backend.database.models import Document, User
from backend.services import ingestion_service
from backend.services.document_service import (
    clean_original_filename,
    extension_for,
    remove_file,
    stream_to_disk,
    upload_root,
    validate_magic,
    validate_reported_type,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Documents"])


def as_response(document: Document) -> DocumentResponse:
    return DocumentResponse(
        id=document.id,
        original_filename=document.original_filename,
        size_bytes=document.size_bytes,
        uploaded_at=document.uploaded_at,
        uploaded_by_name=document.uploaded_by_user.name if document.uploaded_by_user else None,
        ingestion_status=document.ingestion_status,
        ingestion_error=document.ingestion_error,
    )


@router.post("/documents/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    original_filename = clean_original_filename(file.filename)
    extension = extension_for(original_filename)
    try:
        validate_reported_type(extension, file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stored_filename = f"{uuid.uuid4()}{extension}"
    destination = upload_root() / stored_filename
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    try:
        size_bytes, sha256 = await stream_to_disk(file, destination, max_bytes)
        if size_bytes == 0:
            raise HTTPException(status_code=400, detail="Empty files are not allowed")
        validate_magic(destination, extension)
    except OverflowError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except ValueError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Could not validate uploaded file") from None

    duplicate = db.scalar(select(Document).where(Document.sha256 == sha256))
    if duplicate:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="A document with the same contents already exists")

    document = Document(
        original_filename=original_filename,
        stored_filename=stored_filename,
        content_type=file.content_type or "",
        size_bytes=size_bytes,
        sha256=sha256,
        uploaded_by=user.id,
        ingestion_status="pending",
        ingestion_error="AI ingestion not connected yet",
    )
    db.add(document)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=409, detail="A document with the same contents already exists") from None
    db.refresh(document)

    result = ingestion_service.ingest_document(str(destination), document.id, original_filename)
    document.ingestion_status = result.get("status", "pending")
    document.ingestion_error = result.get("error")
    db.commit()
    db.refresh(document)
    return as_response(document)


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("staff", "admin")),
):
    documents = db.scalars(
        select(Document).order_by(Document.uploaded_at.desc())
    ).all()
    return [as_response(document) for document in documents]


@router.delete("/documents/{document_id}", response_model=DocumentDeleteResponse)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    warning = None
    try:
        result = ingestion_service.delete_document(document.id, document.original_filename)
        if result.get("status") != "pending" and result.get("error"):
            warning = result["error"]
    except Exception as exc:
        warning = "AI-side document deletion failed"
        logger.exception("AI-side delete failed for document %s: %s", document.id, exc)

    remove_file(document.stored_filename)
    db.delete(document)
    db.commit()
    return DocumentDeleteResponse(deleted=True, warning=warning)
