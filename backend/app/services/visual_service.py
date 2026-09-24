import io
import logging
import re
from typing import List, Optional
import pymupdf
from sqlalchemy.orm import Session as DBSession

from app.models.file import File
from app.models.document_visual import DocumentVisual
from app.services.file_storage_service import save_file_privately

logger = logging.getLogger(__name__)

# Keywords that indicate user intent to view a diagram / visual
VISUAL_INTENT_PATTERNS = [
    r"\barchitecture\s+diagram\b",
    r"\bsystem\s+architecture\b",
    r"\bflow\s+diagram\b",
    r"\bblock\s+diagram\b",
    r"\bpipeline\s+diagram\b",
    r"\bcomponent\s+diagram\b",
    r"\bdatabase\s+schema\b",
    r"\bdata\s+flow\b",
    r"\bworkflow\s+diagram\b",
    r"\bfigure\b",
    r"\bdiagram\b",
    r"\bchart\b",
    r"\bschema\b",
    r"\bvisual\b",
    r"\bflowchart\b",
]

VISUAL_ACTION_WORDS = ["show", "display", "give", "view", "see", "get", "what does", "illustrate", "draw"]


def detect_visual_intent(query: str) -> bool:
    """
    Deterministically detects whether a user query is asking to see or display
    a document visual, architecture diagram, or figure.
    """
    if not query:
        return False
    q_lower = query.strip().lower()

    # Direct pattern matches
    for pattern in VISUAL_INTENT_PATTERNS:
        if re.search(pattern, q_lower):
            # If the user specifically asks "architecture diagram" or "flow diagram", it's visual intent
            if "diagram" in q_lower or "figure" in q_lower or "chart" in q_lower or "image" in q_lower or "visual" in q_lower or "schema" in q_lower:
                return True
            # If there's an action verb + architecture/visual
            if any(action in q_lower for action in VISUAL_ACTION_WORDS):
                return True

    # Check for visual words combined with request
    has_action = any(action in q_lower for action in VISUAL_ACTION_WORDS)
    has_visual = any(w in q_lower for w in ["architecture", "diagram", "figure", "image", "chart", "schema", "flowchart"])
    if has_action and has_visual:
        return True

    return False


def extract_and_store_document_visuals(
    db: DBSession,
    file_record: File,
    file_bytes: bytes,
) -> List[DocumentVisual]:
    """
    Extracts embedded images and renders vector/diagram pages from documents,
    storing them into private storage and creating DocumentVisual database records.
    """
    ext = (file_record.extension or "").lower()
    visuals: List[DocumentVisual] = []
    visual_idx = 0

    # Case 1: Standalone image uploads (.png, .jpg, .jpeg)
    if ext in (".png", ".jpg", ".jpeg"):
        visual = DocumentVisual(
            file_id=file_record.id,
            visual_index=0,
            page_number=1,
            visual_type="uploaded_image",
            storage_path=file_record.file_path,
            mime_type=file_record.mime_type or "image/png",
            caption=file_record.original_filename,
            context_text=file_record.extracted_text,
        )
        db.add(visual)
        visuals.append(visual)
        db.commit()
        return visuals

    # Case 2: PDF files (.pdf)
    if ext == ".pdf":
        try:
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            for page_idx, page in enumerate(doc):
                page_num = page_idx + 1
                page_text = page.get_text("text") or ""
                page_lower = page_text.lower()

                # Case A: Extract embedded images >= 100x100
                image_list = page.get_images(full=True)
                has_extracted_embedded = False
                for img_info in image_list:
                    xref = img_info[0]
                    try:
                        base_img = doc.extract_image(xref)
                        w = base_img.get("width", 0)
                        h = base_img.get("height", 0)
                        if w >= 100 and h >= 100:
                            img_bytes = base_img["image"]
                            img_ext = "." + base_img.get("ext", "png").lower()
                            mime = f"image/{base_img.get('ext', 'png')}"
                            stored_fn, st_path = save_file_privately(
                                file_bytes=img_bytes,
                                ext=img_ext,
                                mime_type=mime,
                            )
                            visual = DocumentVisual(
                                file_id=file_record.id,
                                visual_index=visual_idx,
                                page_number=page_num,
                                visual_type="embedded_image",
                                storage_path=st_path,
                                mime_type=mime,
                                caption=f"Figure on page {page_num}",
                                context_text=page_text,
                            )
                            db.add(visual)
                            visuals.append(visual)
                            visual_idx += 1
                            has_extracted_embedded = True
                    except Exception as e:
                        logger.debug("Failed extracting embedded image xref=%d: %s", xref, e)

                # Case B: Vector / Diagram page rendering
                # If page has vector drawings or mentions diagram/architecture
                drawings = page.get_drawings()
                is_diagram_page = (
                    len(drawings) >= 5
                    or any(k in page_lower for k in ["architecture", "diagram", "figure", "overview", "flow", "schema", "pipeline", "component", "workflow"])
                )

                if is_diagram_page and not has_extracted_embedded:
                    try:
                        pix = page.get_pixmap(dpi=150)
                        png_bytes = pix.tobytes("png")
                        stored_fn, st_path = save_file_privately(
                            file_bytes=png_bytes,
                            ext=".png",
                            mime_type="image/png",
                        )
                        visual = DocumentVisual(
                            file_id=file_record.id,
                            visual_index=visual_idx,
                            page_number=page_num,
                            visual_type="page_render",
                            storage_path=st_path,
                            mime_type="image/png",
                            caption=f"Page {page_num} document visual",
                            context_text=page_text,
                        )
                        db.add(visual)
                        visuals.append(visual)
                        visual_idx += 1
                    except Exception as e:
                        logger.debug("Failed rendering page %d: %s", page_num, e)

            doc.close()
            db.commit()
        except Exception as e:
            logger.error("Error extracting visuals for file_id=%d: %s", file_record.id, e)

    return visuals


def find_relevant_visual(
    db: DBSession,
    user_id: int,
    query: str,
    qualifying_chunks: Optional[List] = None,
    file_id: Optional[int] = None,
) -> Optional[DocumentVisual]:
    """
    Finds the most relevant DocumentVisual for a visual retrieval query.
    Enforces user ownership strictly.
    """
    base_query = (
        db.query(DocumentVisual)
        .join(File, DocumentVisual.file_id == File.id)
        .filter(File.owner_id == user_id)
    )

    if file_id is not None:
        base_query = base_query.filter(DocumentVisual.file_id == file_id)

    candidates = base_query.all()
    if not candidates:
        return None

    # Priority 1: Match against files in qualifying_chunks
    if qualifying_chunks:
        chunk_file_ids = {c.file_id for c in qualifying_chunks}
        file_candidates = [v for v in candidates if v.file_id in chunk_file_ids]
        if file_candidates:
            # Check for keyword matches in context_text
            q_terms = [t.lower() for t in query.split() if len(t) > 2]
            best_visual = None
            best_matches = -1
            for v in file_candidates:
                ctx_lower = (v.context_text or "").lower()
                matches = sum(1 for t in q_terms if t in ctx_lower)
                if "architecture" in ctx_lower and "architecture" in query.lower():
                    matches += 5
                if "diagram" in ctx_lower:
                    matches += 3
                if matches > best_matches:
                    best_matches = matches
                    best_visual = v
            if best_visual:
                return best_visual

    # Priority 2: Match against query terms across all candidates
    q_terms = [t.lower() for t in query.split() if len(t) > 2]
    best_visual = None
    best_matches = -1
    for v in candidates:
        ctx_lower = (v.context_text or "").lower()
        matches = sum(1 for t in q_terms if t in ctx_lower)
        if "architecture" in ctx_lower and "architecture" in query.lower():
            matches += 5
        if "diagram" in ctx_lower:
            matches += 3
        if matches > best_matches:
            best_matches = matches
            best_visual = v

    return best_visual or candidates[0]
