"""Document upload, listing and deletion."""

import asyncio
import logging
import os
import uuid
from pathlib import Path
from typing import Annotated

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_document_processor, get_vector_store
from app.models.document import Document, utcnow
from app.schemas.document import DocumentDetail, DocumentListItem, DocumentListResponse, DocumentUploadResponse
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import VectorStoreService

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["Documents"])
settings = get_settings()

Db = Annotated[AsyncSession, Depends(get_db)]
CHUNK = 1024 * 1024


async def _save_upload(file: UploadFile, destination: Path, max_bytes: int) -> int:
    """Stream the upload to disk, stopping as soon as it exceeds the size limit."""
    size = 0
    async with aiofiles.open(destination, "wb") as out:
        while block := await file.read(CHUNK):
            size += len(block)
            if size > max_bytes:
                raise HTTPException(status_code=413, detail=f"File too large. Max: {settings.MAX_FILE_SIZE_MB}MB")
            await out.write(block)
    return size


async def _get_active(db: AsyncSession, document_id: uuid.UUID) -> Document:
    document = await db.scalar(select(Document).where(Document.id == document_id, Document.is_active.is_(True)))
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    db: Db,
    file: UploadFile = File(...),
    processor: DocumentProcessor = Depends(get_document_processor),
):
    """Save, parse, chunk, embed and index one file (PDF, TXT, MD, CSV, DOCX)."""
    original_name = os.path.basename(file.filename or "").strip()
    ext = Path(original_name).suffix.lower().lstrip(".")
    if not original_name or ext not in settings.ALLOWED_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_EXTENSIONS)
        raise HTTPException(status_code=400, detail=f"Unsupported file type '.{ext}'. Allowed: {allowed}")

    doc_id = uuid.uuid4()
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{doc_id}.{ext}"

    try:
        size = await _save_upload(file, file_path, settings.MAX_FILE_SIZE_MB * 1024 * 1024)
        # Parsing and embedding are blocking; keep them off the event loop.
        chunk_count = await asyncio.to_thread(processor.process_document, str(file_path), str(doc_id), original_name)
    except HTTPException:
        file_path.unlink(missing_ok=True)
        raise
    except ValueError as exc:  # unreadable or empty document
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        log.exception("Indexing failed for %s", original_name)
        file_path.unlink(missing_ok=True)
        await asyncio.to_thread(processor.vector_store.delete_document, str(doc_id))
        raise HTTPException(status_code=502, detail="Indexing failed. Is the embedding model reachable?") from exc

    document = Document(
        id=doc_id,
        filename=original_name,
        original_filename=original_name,
        file_type=ext,
        file_size=size,
        file_path=str(file_path),
        status="indexed",
        chunk_count=chunk_count,
        processed_at=utcnow(),
    )
    db.add(document)
    await db.commit()
    return document


@router.get("", response_model=DocumentListResponse)
async def list_documents(db: Db, skip: int = 0, limit: int = 20):
    limit = max(1, min(limit, 100))
    active = Document.is_active.is_(True)
    total = await db.scalar(select(func.count(Document.id)).where(active))
    documents = (
        await db.scalars(select(Document).where(active).order_by(Document.uploaded_at.desc()).offset(skip).limit(limit))
    ).all()
    return DocumentListResponse(documents=[DocumentListItem.model_validate(d) for d in documents], total=total or 0)


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(document_id: uuid.UUID, db: Db):
    return await _get_active(db, document_id)


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: uuid.UUID, db: Db, vector_store: VectorStoreService = Depends(get_vector_store)):
    """Soft-delete the record and remove its vectors so it no longer appears in answers."""
    document = await _get_active(db, document_id)
    await asyncio.to_thread(vector_store.delete_document, str(document_id))
    document.is_active = False
    await db.commit()
