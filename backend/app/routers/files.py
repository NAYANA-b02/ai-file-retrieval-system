from typing import List
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.models.user import User
from app.models.file import File as FileModel
from app.schemas.file import FileOut
from app.dependencies.auth import get_current_user
from app.services.file_validation_service import validate_file_metadata, validate_file_content
from app.services.file_storage_service import save_file_privately, persist_file_record
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

    # 4. Metadata Persistence
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

    # 5. Audit Log
    log_audit(
        db=db,
        user_id=current_user.id,
        file_id=file_record.id,
        action="file_upload",
        details=f"Uploaded file: {file.filename} (stored as: {stored_filename})"
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
