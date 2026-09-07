import io
import os
import shutil
from typing import Optional
import pymupdf
import docx
from PIL import Image
import pytesseract

from app.core.config import settings


def _configure_tesseract() -> None:
    """
    Configures pytesseract with the configured local Tesseract binary path
    or falls back to system PATH.
    """
    if settings.TESSERACT_CMD and os.path.exists(settings.TESSERACT_CMD):
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    else:
        # Check if tesseract is in PATH
        which_tesseract = shutil.which("tesseract")
        if which_tesseract:
            pytesseract.pytesseract.tesseract_cmd = which_tesseract


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts text from PDF documents using PyMuPDF.
    """
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    text_chunks = []
    try:
        for page in doc:
            page_text = page.get_text("text")
            if page_text:
                text_chunks.append(page_text.strip())
    finally:
        doc.close()
    return "\n\n".join(chunk for chunk in text_chunks if chunk).strip()


def extract_text_from_docx(file_bytes: bytes) -> str:
    """
    Extracts text from DOCX documents using python-docx.
    """
    doc = docx.Document(io.BytesIO(file_bytes))
    text_parts = []
    for paragraph in doc.paragraphs:
        if paragraph.text:
            text_parts.append(paragraph.text.strip())
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                text_parts.append(row_text)
    return "\n".join(text_parts).strip()


def extract_text_from_txt(file_bytes: bytes) -> str:
    """
    Extracts text from plain text documents using safe multi-encoding decoding.
    """
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return file_bytes.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="replace").strip()


def extract_text_from_image_ocr(file_bytes: bytes) -> str:
    """
    Extracts text from image files (JPG, JPEG, PNG) using pytesseract + Pillow.
    """
    _configure_tesseract()
    image = Image.open(io.BytesIO(file_bytes))
    text = pytesseract.image_to_string(image)
    return text.strip()


def process_file_extraction(extension: str, file_bytes: bytes) -> str:
    """
    Dispatches extraction according to file extension.
    Returns extracted text string.
    Raises exceptions on corrupted or invalid contents.
    """
    ext = extension.lower().strip()
    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext == ".docx":
        return extract_text_from_docx(file_bytes)
    elif ext == ".txt":
        return extract_text_from_txt(file_bytes)
    elif ext in (".jpg", ".jpeg", ".png"):
        return extract_text_from_image_ocr(file_bytes)
    else:
        raise ValueError(f"Unsupported extension for text extraction: '{ext}'")
