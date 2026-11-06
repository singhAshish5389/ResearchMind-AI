"""
ResearchMind AI – Documents API Router
=========================================
Document upload and management endpoints for RAG research.

Endpoints:
  POST   /api/documents           – Upload a document
  GET    /api/documents           – List user's documents
  GET    /api/documents/{id}      – Get document details
  DELETE /api/documents/{id}      – Delete a document
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.database.models import UploadedDocument, User
from app.database.session import get_db
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])

# Allowed MIME types and max file size
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/octet-stream",  # Some browsers send this for .md files
}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
UPLOAD_DIR = Path("uploads/documents")


class DocumentResponse(BaseModel):
    """Document metadata returned by the API."""
    id: str
    filename: str
    original_filename: str
    file_size_bytes: int
    mime_type: str
    chunk_count: int
    page_count: int
    is_indexed: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a Document",
    description=(
        "Upload a PDF or text document for RAG research. "
        "The document will be chunked and indexed in Qdrant. "
        "Requires Qdrant and sentence-transformers to be configured."
    ),
)
async def upload_document(
    file: UploadFile = File(..., description="PDF or text file to upload."),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Upload and index a document for RAG research."""
    # Validate file type
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".txt", ".md"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{suffix}'. Upload PDF, TXT, or MD files.",
        )

    # Read file and validate size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB.",
        )
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Save to filesystem
    document_id = str(uuid.uuid4())
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_filename = f"{document_id}{suffix}"
    file_path = UPLOAD_DIR / safe_filename

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    logger.info(
        "document_uploaded",
        document_id=document_id,
        user_id=current_user.id,
        filename=file.filename,
        size_bytes=len(file_bytes),
    )

    # Create DB record
    doc = UploadedDocument(
        id=document_id,
        user_id=current_user.id,
        filename=safe_filename,
        original_filename=file.filename or "unknown",
        file_size_bytes=len(file_bytes),
        mime_type=file.content_type or "application/octet-stream",
        file_path=str(file_path),
        is_indexed=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    await db.flush()

    # Attempt RAG indexing (non-blocking on failure)
    ingestion_result = None
    try:
        from app.rag.ingestion import ingest_document
        ingestion_result = await ingest_document(
            file_bytes=file_bytes,
            filename=file.filename or safe_filename,
            document_id=document_id,
            user_id=current_user.id,
        )
        doc.chunk_count = ingestion_result["chunk_count"]
        doc.page_count = ingestion_result["page_count"]
        doc.is_indexed = True
        logger.info("document_indexed", document_id=document_id, chunks=doc.chunk_count)
    except Exception as e:
        logger.warning("document_indexing_failed", document_id=document_id, error=str(e))
        # Document is saved but not indexed — user can still see it

    return DocumentResponse.model_validate(doc)


@router.get(
    "",
    response_model=list[DocumentResponse],
    summary="List Documents",
    description="List all uploaded documents for the current user.",
)
async def list_documents(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """List the current user's uploaded documents."""
    result = await db.execute(
        select(UploadedDocument)
        .where(UploadedDocument.user_id == current_user.id)
        .order_by(UploadedDocument.created_at.desc())
    )
    docs = result.scalars().all()
    return [DocumentResponse.model_validate(d) for d in docs]


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get Document",
    description="Get metadata for a specific uploaded document.",
)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Get a document by ID (must belong to current user)."""
    result = await db.execute(
        select(UploadedDocument).where(
            UploadedDocument.id == document_id,
            UploadedDocument.user_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )
    return DocumentResponse.model_validate(doc)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Document",
    description="Delete an uploaded document and remove its vectors from Qdrant.",
)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a document (must belong to current user)."""
    result = await db.execute(
        select(UploadedDocument).where(
            UploadedDocument.id == document_id,
            UploadedDocument.user_id == current_user.id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # Remove from Qdrant
    if doc.is_indexed:
        try:
            from app.rag.ingestion import delete_document as qdrant_delete
            await qdrant_delete(document_id=document_id, user_id=current_user.id)
        except Exception as e:
            logger.warning("qdrant_delete_failed", document_id=document_id, error=str(e))

    # Remove file from filesystem
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except OSError as e:
            logger.warning("file_delete_failed", path=doc.file_path, error=str(e))

    await db.delete(doc)
    logger.info("document_deleted", document_id=document_id, user_id=current_user.id)
