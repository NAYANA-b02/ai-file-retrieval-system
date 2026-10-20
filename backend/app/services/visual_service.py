import io
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
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
    r"\bsoftware\s+architecture\b",
    r"\bcomponent\s+diagram\b",
    r"\bcomponent\s+architecture\b",
    r"\bdeployment\s+diagram\b",
    r"\binfrastructure\s+diagram\b",
    r"\bapplication\s+architecture\b",
    r"\bhigh\s+level\s+design\b",
    r"\bhld\b",
    r"\bsolution\s+workflow\b",
    r"\bprocess\s+workflow\b",
    r"\bprocess\s+flow\b",
    r"\bworkflow\s+diagram\b",
    r"\bpipeline\s+diagram\b",
    r"\bflow\s+diagram\b",
    r"\bflowchart\b",
    r"\bblock\s+diagram\b",
    r"\bdatabase\s+schema\b",
    r"\bschema\s+diagram\b",
    r"\ber\s+diagram\b",
    r"\berd\b",
    r"\bentity\s+relationship\b",
    r"\bdata\s+flow\b",
    r"\bdata\s+flow\s+diagram\b",
    r"\bdfd\b",
    r"\bsequence\s+diagram\b",
    r"\binteraction\s+diagram\b",
    r"\buse\s+case\s+diagram\b",
    r"\bclass\s+diagram\b",
    r"\bfigure\b",
    r"\bdiagram\b",
    r"\bchart\b",
    r"\bgraph\b",
    r"\bschema\b",
    r"\bvisual\b",
    r"\bnext\s+(?:diagram|visual|figure|chart|image)\b",
    r"\banother\s+(?:diagram|visual|figure|chart|image)\b",
]

VISUAL_ACTION_WORDS = [
    "show", "display", "give", "view", "see", "get", "what does",
    "illustrate", "draw", "find", "retrieve", "present"
]

ORDINAL_MAP = {
    "first": 1, "1st": 1, "initial": 1,
    "second": 2, "2nd": 2,
    "third": 3, "3rd": 3,
    "fourth": 4, "4th": 4,
    "fifth": 5, "5th": 5,
    "last": -1, "final": -1,
}

# Meaning-based diagram taxonomy
DIAGRAM_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "system_architecture": {
        "label": "System Architecture",
        "primary_terms": [
            "system architecture", "software architecture", "architecture diagram",
            "component diagram", "component architecture", "application architecture",
            "high level design", "hld", "architecture overview", "technical architecture",
            "system design", "microservice architecture", "deployment architecture",
            "infrastructure architecture", "system overview"
        ],
        "supporting_terms": [
            "frontend", "backend", "client", "server", "api", "database",
            "service", "layer", "stack", "gateway", "microservice", "controller",
            "infrastructure", "cluster", "broker"
        ],
        "conflicting_categories": ["solution_workflow", "database_schema", "use_case_diagram"],
    },
    "solution_workflow": {
        "label": "Solution Workflow",
        "primary_terms": [
            "solution workflow", "workflow diagram", "process flow", "user journey",
            "step by step", "execution flow", "pipeline flow", "flowchart",
            "process diagram", "pipeline stages", "lifecycle", "activity diagram",
            "operational workflow", "procedure flow"
        ],
        "supporting_terms": [
            "step", "stage", "input", "output", "action", "trigger", "flow",
            "start", "end", "proceed", "decision", "validate", "success", "failure"
        ],
        "conflicting_categories": ["system_architecture", "database_schema", "class_diagram"],
    },
    "database_schema": {
        "label": "Database Schema / ERD",
        "primary_terms": [
            "database schema", "schema diagram", "er diagram", "erd",
            "entity relationship", "data model", "relational schema", "table schema"
        ],
        "supporting_terms": [
            "table", "foreign key", "primary key", "column", "entity", "relation",
            "attributes", "cardinality", "one to many", "many to many", "postgres", "sql"
        ],
        "conflicting_categories": ["solution_workflow", "use_case_diagram", "charts_graphs"],
    },
    "data_flow": {
        "label": "Data Flow Diagram",
        "primary_terms": [
            "data flow diagram", "data flow", "dfd", "data pipeline",
            "data ingestion", "data stream", "etl flow", "information flow"
        ],
        "supporting_terms": [
            "stream", "source", "sink", "transform", "queue", "kafka", "batch",
            "ingest", "process data", "consumer", "producer"
        ],
        "conflicting_categories": ["class_diagram", "use_case_diagram"],
    },
    "sequence_diagram": {
        "label": "Sequence Diagram",
        "primary_terms": [
            "sequence diagram", "interaction diagram", "message flow",
            "synchronous call", "asynchronous call", "call sequence"
        ],
        "supporting_terms": [
            "lifeline", "activation", "message", "reply", "return", "request",
            "actor", "timeline", "callback"
        ],
        "conflicting_categories": ["database_schema", "class_diagram", "charts_graphs"],
    },
    "use_case_diagram": {
        "label": "Use Case Diagram",
        "primary_terms": [
            "use case diagram", "use case", "user scenario", "actor diagram"
        ],
        "supporting_terms": [
            "actor", "boundary", "include", "extend", "generalization", "system boundary"
        ],
        "conflicting_categories": ["database_schema", "system_architecture"],
    },
    "class_diagram": {
        "label": "Class Diagram",
        "primary_terms": [
            "class diagram", "uml class", "object diagram", "class hierarchy"
        ],
        "supporting_terms": [
            "class", "interface", "method", "attribute", "inheritance", "composition",
            "aggregation", "polymorphism", "encapsulation"
        ],
        "conflicting_categories": ["solution_workflow", "flowchart"],
    },
    "charts_graphs": {
        "label": "Chart / Graph",
        "primary_terms": [
            "chart", "graph", "bar chart", "pie chart", "line chart",
            "histogram", "plot", "results table", "benchmark graph", "metrics chart"
        ],
        "supporting_terms": [
            "axis", "percentage", "accuracy", "latency", "throughput",
            "benchmark", "metrics", "comparison", "trend", "distribution"
        ],
        "conflicting_categories": ["system_architecture", "database_schema"],
    },
}


def detect_visual_intent(query: str) -> bool:
    """
    Deterministically detects whether a user query is asking to see or display
    a document visual, architecture diagram, workflow, or figure.
    """
    if not query:
        return False
    q_lower = query.strip().lower()

    # Direct pattern matches
    for pattern in VISUAL_INTENT_PATTERNS:
        if re.search(pattern, q_lower):
            # If the user specifically mentions a visual/diagram term
            if any(term in q_lower for term in [
                "diagram", "figure", "chart", "image", "visual", "schema",
                "flowchart", "graph", "architecture", "workflow", "erd"
            ]):
                return True
            # If there's an action verb + visual pattern
            if any(action in q_lower for action in VISUAL_ACTION_WORDS):
                return True

    # Check for visual words combined with request actions
    has_action = any(action in q_lower for action in VISUAL_ACTION_WORDS)
    has_visual = any(w in q_lower for w in [
        "architecture", "diagram", "figure", "image", "chart", "schema",
        "flowchart", "workflow", "erd", "pipeline", "graph"
    ])
    if has_action and has_visual:
        return True

    # Check for ordinal / progression requests (e.g. "show the second diagram", "next diagram")
    if re.search(r"\b(?:first|second|third|1st|2nd|3rd|next|another)\s+(?:diagram|visual|figure|chart|image)\b", q_lower):
        return True

    return False


def detect_query_diagram_category(query: str) -> Optional[str]:
    """
    Identifies the specific diagram type requested in the user query.
    Returns the taxonomy key (e.g., 'system_architecture', 'solution_workflow') or None.
    """
    if not query:
        return None
    q_lower = query.strip().lower()

    best_cat = None
    best_len = 0

    for cat_key, cat_data in DIAGRAM_TAXONOMY.items():
        for term in cat_data["primary_terms"]:
            if re.search(r"\b" + re.escape(term) + r"\b", q_lower):
                # Pick the most specific (longest) phrase match
                if len(term) > best_len:
                    best_len = len(term)
                    best_cat = cat_key

    # Fallback single word checks if no multi-word matched
    if not best_cat:
        if "architecture" in q_lower:
            best_cat = "system_architecture"
        elif "workflow" in q_lower or "flowchart" in q_lower:
            best_cat = "solution_workflow"
        elif "schema" in q_lower or "erd" in q_lower:
            best_cat = "database_schema"
        elif "pipeline" in q_lower or "flow" in q_lower:
            best_cat = "solution_workflow"
        elif "chart" in q_lower or "graph" in q_lower:
            best_cat = "charts_graphs"

    return best_cat


def parse_ordinal_from_query(query: str) -> Optional[int]:
    """
    Parses ordinals like 'first', 'second', '2nd', 'third', 'last' from query.
    Returns 1-based index (e.g. 1, 2, 3) or -1 for last, or None.
    """
    if not query:
        return None
    q_lower = query.strip().lower()

    for word, ord_val in ORDINAL_MAP.items():
        if re.search(r"\b" + re.escape(word) + r"\b", q_lower):
            return ord_val
    return None


def classify_visual_content(
    caption: Optional[str],
    context_text: Optional[str],
) -> Tuple[Optional[str], float, str]:
    """
    Classifies a candidate visual into one of the known diagram categories
    based on its caption, OCR text, and surrounding context.
    Returns: (category_key, confidence_score, display_label)
    """
    full_text = f"{caption or ''} {context_text or ''}".lower()
    if not full_text.strip():
        return None, 0.0, "Document Visual"

    best_cat = None
    best_score = 0.0

    for cat_key, cat_info in DIAGRAM_TAXONOMY.items():
        score = 0.0
        # Check primary terms (each strongly signals this category)
        for term in cat_info["primary_terms"]:
            if re.search(r"\b" + re.escape(term) + r"\b", full_text):
                score += 3.0
                if caption and re.search(r"\b" + re.escape(term) + r"\b", caption.lower()):
                    score += 2.0  # Extra strong if mentioned in caption

        # Check supporting terms
        for term in cat_info.get("supporting_terms", []):
            if re.search(r"\b" + re.escape(term) + r"\b", full_text):
                score += 0.8

        # Subtract conflicting terms to disambiguate (e.g. workflow terms in architecture query)
        for conf_cat in cat_info.get("conflicting_categories", []):
            conf_info = DIAGRAM_TAXONOMY.get(conf_cat, {})
            for term in conf_info.get("primary_terms", []):
                if re.search(r"\b" + re.escape(term) + r"\b", full_text):
                    score -= 1.0

        if score > best_score:
            best_score = score
            best_cat = cat_key

    if best_cat and best_score >= 1.5:
        return best_cat, best_score, DIAGRAM_TAXONOMY[best_cat]["label"]

    return None, 0.0, "Document Visual"


def extract_and_store_document_visuals(
    db: DBSession,
    file_record: File,
    file_bytes: bytes,
) -> List[DocumentVisual]:
    """
    Extracts embedded images and renders vector/diagram pages from documents,
    storing them into private storage and creating DocumentVisual database records.
    Enriches metadata with OCR labels and detected figure captions.
    """
    ext = (file_record.extension or "").lower()
    visuals: List[DocumentVisual] = []
    visual_idx = 0

    # Case 1: Standalone image uploads (.png, .jpg, .jpeg)
    if ext in (".png", ".jpg", ".jpeg"):
        # Try OCR on the uploaded image to capture diagram text/labels
        ocr_text = ""
        try:
            from app.services.text_extraction_service import extract_text_from_image_ocr
            ocr_text = extract_text_from_image_ocr(file_bytes)
        except Exception as ocr_err:
            logger.debug("Image OCR extraction skipped for standalone image: %s", ocr_err)

        context_combined = file_record.extracted_text or ""
        if ocr_text:
            context_combined = f"{context_combined}\n\n[OCR Labels]:\n{ocr_text.strip()}".strip()

        visual = DocumentVisual(
            file_id=file_record.id,
            visual_index=0,
            page_number=1,
            visual_type="uploaded_image",
            storage_path=file_record.file_path,
            mime_type=file_record.mime_type or "image/png",
            caption=file_record.original_filename,
            context_text=context_combined,
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

                # Detect potential figure title / caption on the page
                detected_title = None
                caption_candidates = [
                    r"(?:figure|fig\.?|diagram|chart)\s*\d*[:\.\-]?\s*([A-Za-z0-9\s\-_/]{3,60})",
                    r"\b(system\s+architecture[^\n\r]{0,40})",
                    r"\b(solution\s+workflow[^\n\r]{0,40})",
                    r"\b(data\s+flow[^\n\r]{0,40})",
                    r"\b(database\s+schema[^\n\r]{0,40})",
                    r"\b(component\s+diagram[^\n\r]{0,40})",
                    r"\b(sequence\s+diagram[^\n\r]{0,40})",
                    r"\b(workflow\s+diagram[^\n\r]{0,40})",
                    r"\b(architecture\s+overview[^\n\r]{0,40})",
                ]
                for pat in caption_candidates:
                    m = re.search(pat, page_text, re.IGNORECASE)
                    if m:
                        detected_title = m.group(0).strip().splitlines()[0]
                        break

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

                            # OCR labels from inside the diagram image
                            ocr_text = ""
                            try:
                                from app.services.text_extraction_service import extract_text_from_image_ocr
                                ocr_text = extract_text_from_image_ocr(img_bytes)
                            except Exception:
                                pass

                            context_parts = [page_text]
                            if ocr_text and ocr_text.strip():
                                context_parts.append(f"[OCR Labels]:\n{ocr_text.strip()}")
                            combined_context = "\n\n".join(p for p in context_parts if p.strip())

                            caption_str = detected_title or f"Figure on page {page_num}"

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
                                caption=caption_str[:500],
                                context_text=combined_context,
                            )
                            db.add(visual)
                            visuals.append(visual)
                            visual_idx += 1
                            has_extracted_embedded = True
                    except Exception as e:
                        logger.debug("Failed extracting embedded image xref=%d: %s", xref, e)

                # Case B: Vector / Diagram page rendering
                drawings = page.get_drawings()
                is_diagram_page = (
                    len(drawings) >= 5
                    or any(k in page_lower for k in [
                        "architecture", "diagram", "figure", "overview", "flow",
                        "schema", "pipeline", "component", "workflow", "system"
                    ])
                )

                if is_diagram_page and not has_extracted_embedded:
                    try:
                        pix = page.get_pixmap(dpi=150)
                        png_bytes = pix.tobytes("png")

                        caption_str = detected_title or f"Page {page_num} document visual"

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
                            caption=caption_str[:500],
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


def rank_visual_candidates(
    candidates: List[DocumentVisual],
    query: str,
    qualifying_chunks: Optional[List] = None,
    exclude_visual_ids: Optional[List[int]] = None,
    visual_candidate_index: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Ranks candidate DocumentVisuals by semantic relevance to the requested diagram type,
    using diagram category taxonomy, FastEmbed cosine similarity, caption & OCR evidence,
    and text chunk associations.
    
    Excludes previously viewed or rejected visual IDs.
    Honors ordinals (e.g. 'the second diagram') when requested.
    """
    if not candidates:
        return []

    # Filter out excluded visual IDs (already seen / rejected candidates)
    excluded_set = set(exclude_visual_ids or [])
    remaining = [c for c in candidates if c.id not in excluded_set]
    if not remaining:
        return []

    clean_query = query.strip()
    q_lower = clean_query.lower()

    # 1. Detect target diagram category and ordinal
    target_category = detect_query_diagram_category(clean_query)
    requested_ordinal = parse_ordinal_from_query(clean_query)

    # 2. Build stable document flow order (file_id, page_number, visual_index)
    sorted_by_flow = sorted(
        remaining,
        key=lambda v: (v.file_id, v.page_number or 1, v.visual_index or 0, v.id)
    )
    doc_ordinal_map = {v.id: idx + 1 for idx, v in enumerate(sorted_by_flow)}

    # 3. FastEmbed Semantic Similarity (batch vectorized)
    semantic_scores = [0.0] * len(remaining)
    try:
        from app.services.embedding_service import _get_embedding_model
        emb_model = _get_embedding_model()
        query_emb = next(iter(emb_model.query_embed([clean_query]))).astype(np.float32)
        q_norm = np.linalg.norm(query_emb)
        if q_norm > 0:
            query_emb = query_emb / q_norm

        cand_texts = []
        for v in remaining:
            text_snippet = f"{v.caption or ''}. {v.context_text[:500] if v.context_text else ''}"
            cand_texts.append(text_snippet.strip() or "document visual")

        cand_embs = [e.astype(np.float32) for e in emb_model.embed(cand_texts, batch_size=max(1, len(cand_texts)))]
        for i, c_emb in enumerate(cand_embs):
            c_norm = np.linalg.norm(c_emb)
            if c_norm > 0:
                c_emb = c_emb / c_norm
                sim = float(np.dot(query_emb, c_emb))
                semantic_scores[i] = max(0.0, sim)
    except Exception as emb_err:
        logger.debug("FastEmbed visual ranking fallback: %s", emb_err)
        semantic_scores = [0.0] * len(remaining)

    # 4. Token set for keyword / label overlap
    q_tokens = [t for t in re.findall(r"\b\w+\b", q_lower) if len(t) > 2 and t not in VISUAL_ACTION_WORDS]

    # 5. Score each candidate
    scored_candidates = []
    chunk_file_ids = {c.file_id for c in (qualifying_chunks or [])}

    for idx, visual in enumerate(remaining):
        score = 0.0

        # Component A: Semantic Embedding Similarity (weight: 3.5)
        sim_val = semantic_scores[idx]
        score += sim_val * 3.5

        # Component B: Diagram Content Classification & Category Match
        cand_cat, cat_confidence, display_label = classify_visual_content(
            caption=visual.caption,
            context_text=visual.context_text,
        )

        if target_category:
            if cand_cat == target_category:
                # Strong match on the requested diagram category
                score += 5.0
            elif cand_cat in DIAGRAM_TAXONOMY.get(target_category, {}).get("conflicting_categories", []):
                # Actively conflicting diagram type (e.g. requested architecture, but this is workflow)
                score -= 4.0
            elif cand_cat is not None:
                # Different category
                score -= 1.0

        # Component C: Keyword and Phrase Matches in Caption and Context
        caption_lower = (visual.caption or "").lower()
        context_lower = (visual.context_text or "").lower()
        full_cand_lower = f"{caption_lower} {context_lower}"

        for token in q_tokens:
            if token in full_cand_lower:
                score += 0.5
                if token in caption_lower:
                    score += 1.5  # Extra weight for caption matches

        # Component D: Association with qualifying text chunks from hybrid search
        if visual.file_id in chunk_file_ids:
            score += 1.5
            # Extra boost if a qualifying chunk mentions this exact page
            for chunk in (qualifying_chunks or []):
                if chunk.file_id == visual.file_id and getattr(chunk, 'page_number', None) == visual.page_number:
                    score += 2.0
                    break

        # Component E: Ordinal Targeting (e.g. 'the second diagram')
        if requested_ordinal is not None:
            if requested_ordinal == -1:
                # 'last' diagram
                if doc_ordinal_map.get(visual.id) == len(sorted_by_flow):
                    score += 15.0
            elif doc_ordinal_map.get(visual.id) == requested_ordinal:
                score += 15.0

        scored_candidates.append({
            "visual": visual,
            "score": score,
            "diagram_type": display_label,
            "category": cand_cat,
            "semantic_score": sim_val,
        })

    # Sort descending by composite score, breaking ties by document flow order
    ranked = sorted(
        scored_candidates,
        key=lambda item: (
            item["score"],
            -(item["visual"].page_number or 9999),
            -(item["visual"].visual_index or 0),
        ),
        reverse=True,
    )

    # Compute confidence for top candidate
    if ranked:
        top_score = ranked[0]["score"]
        second_score = ranked[1]["score"] if len(ranked) > 1 else -999.0
        score_margin = top_score - second_score

        if top_score >= 3.0 and (len(ranked) == 1 or score_margin >= 1.5):
            confidence = "high"
        elif top_score >= 1.5 and (len(ranked) == 1 or score_margin >= 0.5):
            confidence = "medium"
        else:
            confidence = "low"

        for r in ranked:
            r["confidence"] = confidence

    return ranked


def find_relevant_visual_candidates(
    db: DBSession,
    user_id: int,
    query: str,
    qualifying_chunks: Optional[List] = None,
    file_id: Optional[int] = None,
    exclude_visual_ids: Optional[List[int]] = None,
    visual_candidate_index: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Main entry point for meaning-based visual retrieval:
    Retrieves, ranks, and filters candidate visuals for a user query.
    Strictly enforces authenticated user document ownership.
    Supports candidate progression and exclusion of rejected diagrams.
    """
    base_query = (
        db.query(DocumentVisual)
        .join(File, DocumentVisual.file_id == File.id)
        .filter(File.owner_id == user_id)
    )

    if file_id is not None:
        base_query = base_query.filter(DocumentVisual.file_id == file_id)

    all_user_candidates = base_query.all()
    if not all_user_candidates:
        return {
            "selected_visual": None,
            "diagram_type": "Document Visual",
            "confidence": "none",
            "candidate_index": 0,
            "candidate_count": 0,
            "has_next_candidate": False,
            "candidate_visual_ids": [],
            "all_exhausted": False,
        }

    # Rank all available candidates
    ranked = rank_visual_candidates(
        candidates=all_user_candidates,
        query=query,
        qualifying_chunks=qualifying_chunks,
        exclude_visual_ids=exclude_visual_ids,
        visual_candidate_index=visual_candidate_index,
    )

    if not ranked:
        # All candidates were excluded / rejected
        return {
            "selected_visual": None,
            "diagram_type": "Document Visual",
            "confidence": "none",
            "candidate_index": 0,
            "candidate_count": 0,
            "has_next_candidate": False,
            "candidate_visual_ids": [],
            "all_exhausted": True,
        }

    # Select candidate: either explicit index or top-ranked
    selected_idx = 0
    if visual_candidate_index is not None and 0 <= visual_candidate_index < len(ranked):
        selected_idx = visual_candidate_index

    selected_item = ranked[selected_idx]
    has_next = (selected_idx + 1) < len(ranked)
    all_candidate_ids = [item["visual"].id for item in ranked]

    return {
        "selected_visual": selected_item["visual"],
        "diagram_type": selected_item["diagram_type"],
        "confidence": selected_item["confidence"],
        "candidate_index": selected_idx,
        "candidate_count": len(ranked),
        "has_next_candidate": has_next,
        "candidate_visual_ids": all_candidate_ids,
        "all_exhausted": False,
    }


def find_relevant_visual(
    db: DBSession,
    user_id: int,
    query: str,
    qualifying_chunks: Optional[List] = None,
    file_id: Optional[int] = None,
) -> Optional[DocumentVisual]:
    """
    Backwards-compatible helper: returns the highest-ranked DocumentVisual
    for a visual retrieval query.
    """
    res = find_relevant_visual_candidates(
        db=db,
        user_id=user_id,
        query=query,
        qualifying_chunks=qualifying_chunks,
        file_id=file_id,
    )
    return res.get("selected_visual")
