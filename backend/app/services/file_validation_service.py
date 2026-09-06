import os
from typing import Tuple
from fastapi import HTTPException, status
from app.core.config import settings

# Allowed extensions and their valid MIME type sets
ALLOWED_TYPES = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/zip"},
    ".txt": {"text/plain"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".png": {"image/png"},
}

# Signatures (magic bytes)
# PDF: starts with %PDF- (hex: 25 50 44 46 2d)
# PNG: starts with 89 50 4E 47 0D 0A 1A 0A
# JPEG: starts with FF D8 FF
# DOCX: ZIP archive starting with PK\x03\x04 (50 4B 03 04)
MAGIC_SIGNATURES = {
    ".pdf": [b"%PDF-"],
    ".png": [b"\x89PNG\r\n\x1a\n"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".docx": [b"PK\x03\x04"],
}


def validate_file_metadata(original_filename: str, declared_mime_type: str, file_size: int) -> Tuple[str, str]:
    """
    Validates file extension, size boundaries, and basic MIME type.
    Returns (cleaned_extension, normalized_mime_type).
    """
    if not original_filename or original_filename.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty"
        )

    _, ext = os.path.splitext(original_filename.strip().lower())
    if not ext or ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_TYPES.keys()))}"
        )

    # Empty file check
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty (0 bytes)"
        )

    # Maximum size check
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({file_size} bytes) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB} MB ({max_bytes} bytes)"
        )

    # Check MIME type
    allowed_mimes = ALLOWED_TYPES[ext]
    norm_declared_mime = declared_mime_type.strip().lower() if declared_mime_type else ""
    if norm_declared_mime not in allowed_mimes:
        # If client passed generic application/octet-stream or mismatched mime, check compatibility
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MIME type '{declared_mime_type}' for extension '{ext}'"
        )

    return ext, norm_declared_mime


def validate_file_content(ext: str, file_bytes: bytes) -> None:
    """
    Validates content signature (magic bytes) where practical.
    """
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content cannot be empty"
        )

    if ext in MAGIC_SIGNATURES:
        signatures = MAGIC_SIGNATURES[ext]
        has_valid_sig = any(file_bytes.startswith(sig) for sig in signatures)
        if not has_valid_sig:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File content signature does not match expected {ext} format"
            )
    elif ext == ".txt":
        # Ensure it is valid text (e.g. decodable as utf-8 or ascii, no binary null bytes)
        try:
            sample = file_bytes[:4096]
            if b"\x00" in sample:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Text file contains null bytes (binary content detected)"
                )
            sample.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text file is not valid UTF-8 text"
            )
