import os
import uuid
from pathlib import Path
from typing import Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.file import File
from app.models.user import User


def get_private_upload_dir() -> Path:
    """
    Returns the resolved absolute Path to the private upload directory,
    creating it if it does not already exist.
    """
    upload_path = Path(settings.UPLOAD_DIR)
    if not upload_path.is_absolute():
        # Resolve relative to backend base directory
        backend_dir = Path(__file__).resolve().parent.parent.parent
        upload_path = (backend_dir / upload_path).resolve()
    
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path


def generate_stored_filename(ext: str) -> str:
    """
    Generates a UUID-v4-based stored filename with extension.
    Never uses the original filename.
    """
    return f"{uuid.uuid4()}{ext}"


def save_file_privately(file_bytes: bytes, ext: str) -> Tuple[str, str]:
    """
    Saves the file bytes to the private upload directory using a generated UUID stored filename.
    Guarantees path traversal prevention and ensures uploaded files cannot escape the upload directory.
    Returns (stored_filename, absolute_file_path).
    """
    upload_dir = get_private_upload_dir()
    stored_filename = generate_stored_filename(ext)

    # Path traversal check
    target_path = (upload_dir / stored_filename).resolve()
    try:
        target_path.relative_to(upload_dir)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Illegal file storage path attempt detected"
        )

    # Write file securely
    with open(target_path, "wb") as f:
        f.write(file_bytes)

    return stored_filename, str(target_path)


def persist_file_record(
    db: Session,
    owner_id: int,
    original_filename: str,
    stored_filename: str,
    file_path: str,
    extension: str,
    mime_type: str,
    size: int
) -> File:
    """
    Persists file metadata into PostgreSQL.
    """
    # Clean original filename to prevent directory traversal notation in display filename
    clean_original_filename = os.path.basename(original_filename)

    file_record = File(
        owner_id=owner_id,
        original_filename=clean_original_filename,
        stored_filename=stored_filename,
        file_path=file_path,
        extension=extension,
        mime_type=mime_type,
        size=size,
        processing_status="uploaded",
        text_chunk_count=0
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)
    return file_record
