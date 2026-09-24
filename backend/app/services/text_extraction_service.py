import io
import logging
import os
import shutil
from typing import Optional
import pymupdf
import docx
from PIL import Image, ImageOps
import pytesseract

from app.core.config import settings

logger = logging.getLogger(__name__)


def _configure_tesseract() -> Optional[str]:
    """
    Configures pytesseract with the configured Tesseract binary path
    or discovers it from system PATH and standard Linux/Mac/Windows paths.
    Returns the resolved path, or None if not found.
    """
    resolved_path: Optional[str] = None

    # 1. Configured TESSERACT_CMD if existing
    if settings.TESSERACT_CMD and os.path.exists(settings.TESSERACT_CMD):
        resolved_path = settings.TESSERACT_CMD

    # 2. Check if tesseract is in PATH
    if not resolved_path:
        which_tesseract = shutil.which("tesseract")
        if which_tesseract:
            resolved_path = which_tesseract

    # 3. Check standard Linux/Unix/Mac/Container installations
    if not resolved_path:
        standard_paths = [
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/opt/homebrew/bin/tesseract",
            os.path.expanduser("~/.local/usr/bin/tesseract"),
            os.path.expanduser("~/.local/bin/tesseract"),
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for p in standard_paths:
            if os.path.exists(p):
                resolved_path = p
                break

    if resolved_path:
        pytesseract.pytesseract.tesseract_cmd = resolved_path

        # Also set TESSDATA_PREFIX if not explicitly configured in environment
        if "TESSDATA_PREFIX" not in os.environ:
            tessdata_candidates = [
                "/usr/share/tesseract-ocr/5/tessdata",
                "/usr/share/tesseract-ocr/4.00/tessdata",
                "/usr/share/tessdata",
                "/usr/local/share/tessdata",
                os.path.expanduser("~/.local/usr/share/tesseract-ocr/5/tessdata"),
                r"C:\Program Files\Tesseract-OCR\tessdata",
            ]
            for td in tessdata_candidates:
                if os.path.isdir(td):
                    os.environ["TESSDATA_PREFIX"] = td
                    break

        return resolved_path

    return None


def verify_tesseract_installation() -> tuple[Optional[str], Optional[str]]:
    """
    Verifies that Tesseract is discovered and executable.
    Returns (binary_path, version_string) or (None, None).
    """
    path = _configure_tesseract()
    if not path:
        return None, None
    try:
        import subprocess
        res = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
        first_line = res.stdout.splitlines()[0] if res.stdout else "available"
        return path, first_line.strip()
    except Exception as e:
        logger.debug("Failed running tesseract --version: %s", e)
        return path, "available"


def extract_text_from_image_ocr(file_bytes: bytes) -> str:
    """
    Extracts text from image files (JPG, JPEG, PNG) using pytesseract + Pillow.
    Normalizes image orientation (EXIF) and color mode (RGB) for robust OCR.
    """
    _configure_tesseract()
    try:
        image = Image.open(io.BytesIO(file_bytes))
        # Handle EXIF orientation if present
        image = ImageOps.exif_transpose(image)
        # Convert to RGB if needed (handles RGBA, CMYK, P, 1)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        text = pytesseract.image_to_string(image)
        return text.strip()
    except pytesseract.pytesseract.TesseractNotFoundError:
        logger.warning("Tesseract binary not found. OCR cannot be performed.")
        raise RuntimeError("Tesseract OCR is not installed or configured on the server")
    except Exception as e:
        logger.error("OCR extraction failed: %s", e)
        raise


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extracts text from PDF documents using PyMuPDF.
    If a page contains little or no text (< 10 chars), falls back to rendering
    the page to an image and performing OCR (for scanned PDF pages).
    """
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    text_chunks = []
    try:
        for page_idx, page in enumerate(doc):
            page_text = page.get_text("text").strip()
            # If page text is meaningful, use it directly
            if len(page_text) >= 10:
                text_chunks.append(page_text)
            else:
                # Scanned page fallback: render to image and run OCR
                try:
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    ocr_text = extract_text_from_image_ocr(img_bytes)
                    if ocr_text:
                        text_chunks.append(ocr_text)
                    elif page_text:
                        text_chunks.append(page_text)
                except Exception as ocr_err:
                    logger.debug("Page %d OCR fallback failed: %s", page_idx + 1, ocr_err)
                    if page_text:
                        text_chunks.append(page_text)
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

