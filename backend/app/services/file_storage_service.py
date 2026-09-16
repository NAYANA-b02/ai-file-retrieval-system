import logging
import os
import uuid
from pathlib import Path
from typing import Tuple, Optional
import httpx
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.file import File
from app.models.user import User

logger = logging.getLogger(__name__)


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


def upload_to_supabase_storage(
    file_bytes: bytes,
    stored_filename: str,
    mime_type: str = "application/octet-stream",
) -> str:
    """
    Uploads file bytes directly to the private Supabase Storage bucket via REST API.
    Authenticates using the server-side Secret key.
    Never exposes credentials in logs, exceptions, or errors.
    Returns storage reference URI: supabase://<bucket>/<stored_filename>.
    """
    base_url = settings.SUPABASE_URL.rstrip("/")
    bucket = settings.SUPABASE_STORAGE_BUCKET
    url = f"{base_url}/storage/v1/object/{bucket}/{stored_filename}"

    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
        "apikey": settings.SUPABASE_SECRET_KEY,
        "Content-Type": mime_type or "application/octet-stream",
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, content=file_bytes)

        if response.status_code >= 400:
            logger.error(
                "Supabase Storage upload failed for file %s with HTTP status %d",
                stored_filename,
                response.status_code,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store file in remote storage",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Supabase Storage upload encountered an error for file %s: %s",
            stored_filename,
            type(exc).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store file in remote storage",
        )

    return f"supabase://{bucket}/{stored_filename}"


def save_file_privately(
    file_bytes: bytes,
    ext: str,
    mime_type: str = "application/octet-stream",
) -> Tuple[str, str]:
    """
    Saves the file bytes privately:
    - If SUPABASE_URL and SUPABASE_SECRET_KEY are configured, uploads to the private
      Supabase Storage bucket and returns (stored_filename, supabase://<bucket>/<stored_filename>).
    - Otherwise, saves to the local private upload directory using UUID stored filename
      and returns (stored_filename, absolute_file_path).
    Guarantees path traversal prevention and ensures zero credential exposure.
    """
    stored_filename = generate_stored_filename(ext)

    if settings.SUPABASE_URL and settings.SUPABASE_SECRET_KEY:
        storage_path = upload_to_supabase_storage(
            file_bytes=file_bytes,
            stored_filename=stored_filename,
            mime_type=mime_type,
        )
        return stored_filename, storage_path

    # Local fallback for development and unit testing
    upload_dir = get_private_upload_dir()

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


def update_file_processing_result(
    db: Session,
    file_id: int,
    status: str,
    extracted_text: Optional[str] = None,
    error_message: Optional[str] = None
) -> Optional[File]:
    """
    Updates processing_status, extracted_text, and error_message of a File record.
    """
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        return None

    file_record.processing_status = status
    if extracted_text is not None:
        file_record.extracted_text = extracted_text
    if error_message is not None:
        file_record.error_message = error_message

    db.commit()
    db.refresh(file_record)
    return file_record


def get_file_bytes(file_record: File) -> bytes:
    """
    Retrieves raw file content bytes from either Supabase Storage or local private upload dir.
    Never exposes physical filesystem paths or storage credentials in exceptions.
    """
    storage_path = file_record.file_path or ""
    if storage_path.startswith("supabase://"):
        if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Remote storage is not properly configured",
            )
        parts = storage_path.replace("supabase://", "").split("/", 1)
        if len(parts) != 2:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid remote storage reference format",
            )
        bucket, stored_filename = parts[0], parts[1]
        base_url = settings.SUPABASE_URL.rstrip("/")
        url = f"{base_url}/storage/v1/object/{bucket}/{stored_filename}"
        headers = {
            "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
            "apikey": settings.SUPABASE_SECRET_KEY,
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url, headers=headers)
            if resp.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File content not found in remote storage",
                )
            if resp.status_code >= 400:
                logger.error("Supabase Storage get failed with status %d", resp.status_code)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to retrieve file from remote storage",
                )
            return resp.content
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Error retrieving file from Supabase Storage: %s", type(exc).__name__)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve file from remote storage",
            )

    # Local filesystem storage
    file_path = Path(storage_path)
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File content not found on server",
        )
    try:
        with open(file_path, "rb") as f:
            return f.read()
    except Exception as exc:
        logger.error("Error reading local file: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read file from storage",
        )


def delete_file_from_storage(file_record: File) -> None:
    """
    Deletes the underlying binary file from Supabase Storage or local upload directory.
    Fails silently with a warning if the file was already missing.
    """
    storage_path = file_record.file_path or ""
    if storage_path.startswith("supabase://"):
        if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
            logger.warning("Cannot delete remote file: Supabase credentials not set")
            return
        parts = storage_path.replace("supabase://", "").split("/", 1)
        if len(parts) != 2:
            return
        bucket, stored_filename = parts[0], parts[1]
        base_url = settings.SUPABASE_URL.rstrip("/")
        url = f"{base_url}/storage/v1/object/{bucket}/{stored_filename}"
        headers = {
            "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
            "apikey": settings.SUPABASE_SECRET_KEY,
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                client.delete(url, headers=headers)
        except Exception as exc:
            logger.warning("Failed to delete file from Supabase Storage: %s", exc)
        return

    # Local file deletion
    try:
        path = Path(storage_path)
        if path.is_file():
            path.unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Failed to delete local file: %s", exc)

