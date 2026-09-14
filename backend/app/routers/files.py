import logging
from typing import List
from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.core.database import SessionLocal, get_db
from app.models.user import User
from app.models.file import File as FileModel
from app.schemas.file import FileOut
from app.dependencies.auth import get_current_user
from app.services.file_validation_service import validate_file_metadata, validate_file_content
from app.services.file_storage_service import (
    save_file_privately,
    persist_file_record,
    update_file_processing_result,
)
from app.services.text_extraction_service import process_file_extraction
from app.services.embedding_service import process_chunking_and_embedding
from app.services.audit_service import log_audit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/files", tags=["Files"])


def _process_file_in_background(file_id: int) -> None:
    """
    Background task to generate text chunks and embeddings for an uploaded file.
    Uses a fresh database session and ensures it is closed in finally.
    """
    db = SessionLocal()
    try:
        process_chunking_and_embedding(db=db, file_id=file_id)
    except Exception:
        logger.exception("Unexpected error in background chunking/embedding for file_id=%d", file_id)
    finally:
        db.close()


@router.post("/upload", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    Uploads a file securely:
    - Requires session authentication
    - Validates extension, MIME type, size, and content signature
    - Stores file in private directory using UUID filename
    - Saves metadata to database
    - Extracts text (PDF, DOCX, TXT) or performs OCR (JPG, JPEG, PNG)
    - Updates processing_status ('processing' or 'failed') and extracted_text
    - Dispatches heavy chunking & embedding as a FastAPI BackgroundTask
    - Never exposes physical server filesystem paths
    """
    file_bytes = await file.read()
    file_size = len(file_bytes)

    # 1. Validation (extension, size, empty check, MIME type)
    ext, mime_type = validate_file_metadata(
        original_filename=file.filename or "",
        declared_mime_type=file.content_type or "",
        file_size=file_size,
    )

    # 2. Content signature verification (magic bytes)
    validate_file_content(ext=ext, file_bytes=file_bytes)

    # 3. Private Storage (UUID filename, path traversal check)
    stored_filename, physical_path = save_file_privately(file_bytes=file_bytes, ext=ext)

    # 4. Metadata Persistence (Initial status)
    file_record = persist_file_record(
        db=db,
        owner_id=current_user.id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        file_path=physical_path,
        extension=ext,
        mime_type=mime_type,
        size=file_size,
    )

    # 5. Phase 4: Text Extraction & OCR Processing
    extraction_succeeded = False
    has_meaningful_text = False
    try:
        extracted_text = process_file_extraction(extension=ext, file_bytes=file_bytes)
        extraction_succeeded = True
        has_meaningful_text = bool(extracted_text and extracted_text.strip())

        if has_meaningful_text:
            update_file_processing_result(
                db=db,
                file_id=file_record.id,
                status="processing",
                extracted_text=extracted_text,
                error_message=None,
            )
        else:
            # Empty or whitespace-only text: successfully processed with 0 chunks
            update_file_processing_result(
                db=db,
                file_id=file_record.id,
                status="completed",
                extracted_text=extracted_text,
                error_message=None,
            )
    except Exception as e:
        # Sanitize error message to prevent leaking physical server filesystem paths
        safe_error = f"Text extraction failed: {type(e).__name__}"
        update_file_processing_result(
            db=db,
            file_id=file_record.id,
            status="failed",
            extracted_text=None,
            error_message=safe_error,
        )

    db.refresh(file_record)

    # 6. Phase 5: Asynchronous Background Text Chunking & Embedding
    if extraction_succeeded and has_meaningful_text:
        background_tasks.add_task(_process_file_in_background, file_record.id)

    # 7. Audit Log
    log_audit(
        db=db,
        user_id=current_user.id,
        file_id=file_record.id,
        action="file_upload",
        details=f"Uploaded file: {file.filename} (status: {file_record.processing_status})",
    )

    return file_record


@router.get("", response_model=List[FileOut])
def list_files(
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    Lists files owned exclusively by the current authenticated user.
    Never returns another user's files.
    Excludes physical filesystem paths.
    """
    files = (
        db.query(FileModel)
        .filter(FileModel.owner_id == current_user.id)
        .order_by(FileModel.uploaded_at.desc())
        .all()
    )
    return files


@router.get("/{file_id}", response_model=FileOut)
def get_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    Retrieves metadata and extracted text for a file owned by current authenticated user.
    Returns 404 if file does not exist or belongs to another user.
    Excludes physical filesystem paths.
    """
    file_record = (
        db.query(FileModel)
        .filter(FileModel.id == file_id, FileModel.owner_id == current_user.id)
        .first()
    )
    if not file_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    return file_record

