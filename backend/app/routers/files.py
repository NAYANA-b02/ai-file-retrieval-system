from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
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

router = APIRouter(prefix="/api/v1/files", tags=["Files"])


@router.post("/upload", response_model=FileOut, status_code=status.HTTP_201_CREATED)
async def upload_file(
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
    - Updates processing_status ('completed' or 'failed') and extracted_text
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
    try:
        extracted_text = process_file_extraction(extension=ext, file_bytes=file_bytes)
        update_file_processing_result(
            db=db,
            file_id=file_record.id,
            status="completed",
            extracted_text=extracted_text,
            error_message=None
        )
    except Exception as e:
        # Sanitize error message to prevent leaking physical server filesystem paths
        safe_error = f"Text extraction failed: {type(e).__name__}"
        update_file_processing_result(
            db=db,
            file_id=file_record.id,
            status="failed",
            extracted_text=None,
            error_message=safe_error
        )

    db.refresh(file_record)

    # 6. Phase 5: Text Chunking & Embedding
    if file_record.processing_status == "completed":
        process_chunking_and_embedding(db=db, file_id=file_record.id)
        db.refresh(file_record)

    # 7. Audit Log
    log_audit(
        db=db,
        user_id=current_user.id,
        file_id=file_record.id,
        action="file_upload",
        details=f"Uploaded file: {file.filename} (status: {file_record.processing_status})"
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

