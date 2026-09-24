import logging
import re
from typing import List, Optional
import numpy as np
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.models.file import File
from app.models.text_chunk import TextChunk
from app.schemas.search import (
    HighlightRange,
    SearchResultItem,
    SemanticSearchResponse,
    KeywordSearchResponse,
    HybridSearchResponse,
)
from app.services.embedding_service import _get_embedding_model, deserialize_embedding
from app.services.audit_service import log_audit

logger = logging.getLogger(__name__)


def compute_keyword_highlights(chunk_text: str, query: str) -> List[HighlightRange]:
    """
    Identifies exact matching query terms in chunk text and returns character start/end ranges.
    Case-insensitive, supports multiple query terms, preserves original casing.
    """
    if not chunk_text or not query:
        return []

    tokens = set(re.findall(r'\b\w+\b', query.lower()))
    # Keep words with length >= 2 or alphanumeric
    tokens = {t for t in tokens if len(t) >= 2 or t.isalnum()}
    if not tokens:
        return []

    escaped = [re.escape(t) for t in sorted(tokens, key=len, reverse=True)]
    if not escaped:
        return []

    # First attempt whole word boundary match
    pattern = re.compile(r'\b(' + '|'.join(escaped) + r')\b', re.IGNORECASE)
    matches = list(pattern.finditer(chunk_text))

    # If no word-boundary match, attempt substring match
    if not matches:
        pattern = re.compile('|'.join(escaped), re.IGNORECASE)
        matches = list(pattern.finditer(chunk_text))

    highlights: List[HighlightRange] = []
    for m in matches:
        highlights.append(HighlightRange(start=m.start(), end=m.end(), type="keyword"))
    return highlights


def compute_semantic_highlights(
    chunk_text: str,
    query_emb: np.ndarray,
    model=None,
) -> List[HighlightRange]:
    """
    Segments chunk text into sentences/passages and identifies the most semantically
    relevant passage using cosine similarity against the query embedding.
    """
    if not chunk_text or query_emb is None:
        return []

    # Split into sentence spans
    spans = []
    for match in re.finditer(r'[^.!?\n]+[.!?\n]*', chunk_text):
        span_text = match.group().strip()
        if len(span_text) >= 15:  # Filter out trivial fragments
            spans.append((match.start(), match.end(), span_text))

    # If only 1 span or text is short, highlight the entire meaningful text
    if len(spans) <= 1:
        start_idx = 0
        end_idx = len(chunk_text.rstrip())
        return [HighlightRange(start=start_idx, end=end_idx, type="semantic")]

    if model is None:
        model = _get_embedding_model()

    # Embed candidate sentences
    sentence_texts = [s[2] for s in spans]
    try:
        sent_embs = list(model.embed(sentence_texts, batch_size=16))
        sent_norms = [np.linalg.norm(e) for e in sent_embs]
        scores = []
        for emb, norm in zip(sent_embs, sent_norms):
            if norm > 0:
                scores.append(float(np.dot(emb / norm, query_emb)))
            else:
                scores.append(0.0)

        best_idx = int(np.argmax(scores))
        best_span = spans[best_idx]
        return [HighlightRange(start=best_span[0], end=best_span[1], type="semantic")]
    except Exception as e:
        logger.debug("Sentence-level semantic highlight scoring failed: %s", e)
        return [HighlightRange(start=spans[0][0], end=spans[0][1], type="semantic")]


def _validate_file_filter(db: DBSession, user_id: int, file_id: Optional[int]) -> None:
    """Verifies that if a file_id is provided, the file exists and is owned by user."""
    if file_id is not None:
        file_record = (
            db.query(File)
            .filter(File.id == file_id, File.owner_id == user_id)
            .first()
        )
        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found or access denied",
            )


def execute_semantic_search(
    db: DBSession,
    user_id: int,
    query: str,
    top_k: int = 5,
    file_id: Optional[int] = None,
) -> SemanticSearchResponse:
    """
    Perform semantic search across document chunks belonging strictly to the user,
    optionally restricted to a single file_id.
    """
    if not query or not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty or whitespace only",
        )

    clean_query = query.strip()

    if top_k < 1 or top_k > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="top_k must be between 1 and 50",
        )

    _validate_file_filter(db, user_id, file_id)

    db_query = (
        db.query(TextChunk, File)
        .join(File, TextChunk.file_id == File.id)
        .filter(File.owner_id == user_id)
        .filter(File.processing_status == "completed")
    )

    if file_id is not None:
        db_query = db_query.filter(File.id == file_id)

    rows = db_query.all()
    valid_rows = [(chunk, file_record) for chunk, file_record in rows if chunk.embedding]

    if not valid_rows:
        log_audit(
            db=db,
            user_id=user_id,
            action="semantic_search",
            query=clean_query,
            file_id=file_id,
            details=f"Semantic search: top_k={top_k}, file_id={file_id}, results=0",
        )
        return SemanticSearchResponse(
            query=clean_query,
            search_mode="semantic",
            file_id=file_id,
            total_results=0,
            results=[],
        )

    model = _get_embedding_model()
    query_emb = next(iter(model.query_embed([clean_query]))).astype(np.float32)
    query_norm = np.linalg.norm(query_emb)
    if query_norm > 0:
        query_emb = query_emb / query_norm

    chunk_embeddings = np.vstack([deserialize_embedding(chunk.embedding) for chunk, _ in valid_rows])
    chunk_norms = np.linalg.norm(chunk_embeddings, axis=1, keepdims=True)
    chunk_norms[chunk_norms == 0] = 1e-10
    normalized_chunks = chunk_embeddings / chunk_norms

    similarity_scores = np.dot(normalized_chunks, query_emb)
    ranked_indices = np.argsort(-similarity_scores)[:top_k]

    results: List[SearchResultItem] = []
    for idx in ranked_indices:
        chunk, file_record = valid_rows[idx]
        score = float(similarity_scores[idx])

        # Compute semantic highlight range (and any token matches)
        highlights = compute_semantic_highlights(chunk.chunk_text, query_emb, model)
        kw_highlights = compute_keyword_highlights(chunk.chunk_text, clean_query)
        if kw_highlights:
            highlights.extend(kw_highlights)

        results.append(
            SearchResultItem(
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.chunk_text,
                file_id=file_record.id,
                original_filename=file_record.original_filename,
                similarity_score=round(score, 4),
                semantic_score=round(score, 4),
                extension=file_record.extension,
                mime_type=file_record.mime_type,
                uploaded_at=file_record.uploaded_at,
                highlight_ranges=highlights,
            )
        )

    log_audit(
        db=db,
        user_id=user_id,
        action="semantic_search",
        query=clean_query,
        file_id=file_id,
        details=f"Semantic search: top_k={top_k}, file_id={file_id}, results={len(results)}",
    )

    return SemanticSearchResponse(
        query=clean_query,
        search_mode="semantic",
        file_id=file_id,
        total_results=len(results),
        results=results,
    )


def execute_keyword_search(
    db: DBSession,
    user_id: int,
    query: str,
    top_k: int = 5,
    file_id: Optional[int] = None,
) -> KeywordSearchResponse:
    """
    Perform keyword-based search over document chunks owned by the authenticated user,
    optionally restricted to a single file_id.
    """
    if not query or not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty or whitespace only",
        )

    clean_query = query.strip()

    if top_k < 1 or top_k > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="top_k must be between 1 and 50",
        )

    _validate_file_filter(db, user_id, file_id)

    ts_vector = func.to_tsvector("english", TextChunk.chunk_text)
    ts_query = func.plainto_tsquery("english", clean_query)
    fts_rank_expr = func.ts_rank_cd(ts_vector, ts_query)

    db_query = (
        db.query(TextChunk, File, fts_rank_expr.label("fts_rank"))
        .join(File, TextChunk.file_id == File.id)
        .filter(File.owner_id == user_id)
        .filter(File.processing_status == "completed")
    )

    if file_id is not None:
        db_query = db_query.filter(File.id == file_id)

    rows = db_query.all()

    if not rows:
        log_audit(
            db=db,
            user_id=user_id,
            action="keyword_search",
            query=clean_query,
            file_id=file_id,
            details=f"Keyword search: top_k={top_k}, file_id={file_id}, results=0",
        )
        return KeywordSearchResponse(
            query=clean_query,
            search_mode="keyword",
            file_id=file_id,
            total_results=0,
            results=[],
        )

    terms = [t.lower() for t in clean_query.split() if t.strip()]
    query_lower = clean_query.lower()

    scored_items = []
    for chunk, file_record, fts_rank in rows:
        chunk_lower = chunk.chunk_text.lower()
        fts_score = float(fts_rank or 0.0)
        phrase_match = 1.0 if query_lower in chunk_lower else 0.0
        term_matches = sum(1 for t in terms if t in chunk_lower)
        term_ratio = (term_matches / len(terms)) if terms else 0.0

        raw_kw = fts_score + (0.5 * phrase_match) + (0.5 * term_ratio)
        if raw_kw > 0:
            scored_items.append((raw_kw, chunk, file_record))

    if not scored_items:
        log_audit(
            db=db,
            user_id=user_id,
            action="keyword_search",
            query=clean_query,
            file_id=file_id,
            details=f"Keyword search: top_k={top_k}, file_id={file_id}, results=0",
        )
        return KeywordSearchResponse(
            query=clean_query,
            search_mode="keyword",
            file_id=file_id,
            total_results=0,
            results=[],
        )

    scored_items.sort(key=lambda x: x[0], reverse=True)
    max_score = scored_items[0][0]

    top_items = scored_items[:top_k]
    results: List[SearchResultItem] = []
    for raw_score, chunk, file_record in top_items:
        normalized_score = round(raw_score / max_score, 4) if max_score > 0 else 0.0
        highlights = compute_keyword_highlights(chunk.chunk_text, clean_query)

        results.append(
            SearchResultItem(
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.chunk_text,
                file_id=file_record.id,
                original_filename=file_record.original_filename,
                similarity_score=normalized_score,
                keyword_score=normalized_score,
                extension=file_record.extension,
                mime_type=file_record.mime_type,
                uploaded_at=file_record.uploaded_at,
                highlight_ranges=highlights,
            )
        )

    log_audit(
        db=db,
        user_id=user_id,
        action="keyword_search",
        query=clean_query,
        file_id=file_id,
        details=f"Keyword search: top_k={top_k}, file_id={file_id}, results={len(results)}",
    )

    return KeywordSearchResponse(
        query=clean_query,
        search_mode="keyword",
        file_id=file_id,
        total_results=len(results),
        results=results,
    )


def execute_hybrid_search(
    db: DBSession,
    user_id: int,
    query: str,
    top_k: int = 5,
    keyword_weight: Optional[float] = None,
    semantic_weight: Optional[float] = None,
    file_id: Optional[int] = None,
) -> HybridSearchResponse:
    """
    Perform hybrid search combining keyword relevance and semantic similarity,
    optionally restricted to a single file_id.
    """
    if not query or not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty or whitespace only",
        )

    clean_query = query.strip()

    if top_k < 1 or top_k > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="top_k must be between 1 and 50",
        )

    _validate_file_filter(db, user_id, file_id)

    kw_w = settings.KEYWORD_SEARCH_WEIGHT if keyword_weight is None else keyword_weight
    sem_w = settings.SEMANTIC_SEARCH_WEIGHT if semantic_weight is None else semantic_weight

    if kw_w < 0.0 or sem_w < 0.0 or (kw_w + sem_w) <= 0.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Weights must be non-negative and sum to greater than 0",
        )

    total_w = kw_w + sem_w
    norm_kw_w = kw_w / total_w
    norm_sem_w = sem_w / total_w

    ts_vector = func.to_tsvector("english", TextChunk.chunk_text)
    ts_query = func.plainto_tsquery("english", clean_query)
    fts_rank_expr = func.ts_rank_cd(ts_vector, ts_query)

    db_query = (
        db.query(TextChunk, File, fts_rank_expr.label("fts_rank"))
        .join(File, TextChunk.file_id == File.id)
        .filter(File.owner_id == user_id)
        .filter(File.processing_status == "completed")
    )

    if file_id is not None:
        db_query = db_query.filter(File.id == file_id)

    rows = db_query.all()
    valid_rows = [(chunk, file_record, float(fts_rank or 0.0)) for chunk, file_record, fts_rank in rows if chunk.embedding]

    if not valid_rows:
        log_audit(
            db=db,
            user_id=user_id,
            action="hybrid_search",
            query=clean_query,
            file_id=file_id,
            details=f"Hybrid search: top_k={top_k}, file_id={file_id}, results=0",
        )
        return HybridSearchResponse(
            query=clean_query,
            search_mode="hybrid",
            file_id=file_id,
            keyword_weight=round(norm_kw_w, 4),
            semantic_weight=round(norm_sem_w, 4),
            total_results=0,
            results=[],
        )

    # 1. Semantic Scoring
    model = _get_embedding_model()
    query_emb = next(iter(model.query_embed([clean_query]))).astype(np.float32)
    query_norm = np.linalg.norm(query_emb)
    if query_norm > 0:
        query_emb = query_emb / query_norm

    chunk_embeddings = np.vstack([deserialize_embedding(chunk.embedding) for chunk, _, _ in valid_rows])
    chunk_norms = np.linalg.norm(chunk_embeddings, axis=1, keepdims=True)
    chunk_norms[chunk_norms == 0] = 1e-10
    normalized_chunks = chunk_embeddings / chunk_norms

    raw_sem_scores = np.dot(normalized_chunks, query_emb)
    sem_scores_norm = np.maximum(0.0, raw_sem_scores)

    # 2. Keyword Scoring
    terms = [t.lower() for t in clean_query.split() if t.strip()]
    query_lower = clean_query.lower()

    raw_kw_scores = []
    for chunk, _, fts_rank in valid_rows:
        chunk_lower = chunk.chunk_text.lower()
        phrase_match = 1.0 if query_lower in chunk_lower else 0.0
        term_matches = sum(1 for t in terms if t in chunk_lower)
        term_ratio = (term_matches / len(terms)) if terms else 0.0
        raw_kw = fts_rank + (0.5 * phrase_match) + (0.5 * term_ratio)
        raw_kw_scores.append(raw_kw)

    raw_kw_arr = np.array(raw_kw_scores, dtype=np.float32)
    max_kw = float(np.max(raw_kw_arr)) if len(raw_kw_arr) > 0 else 0.0
    if max_kw > 0.0:
        kw_scores_norm = raw_kw_arr / max_kw
    else:
        kw_scores_norm = np.zeros_like(raw_kw_arr)

    # 3. Weighted Combined Score
    hybrid_scores = (norm_sem_w * sem_scores_norm) + (norm_kw_w * kw_scores_norm)

    # 4. Rank descending by hybrid score
    ranked_indices = np.argsort(-hybrid_scores)[:top_k]

    results: List[SearchResultItem] = []
    for idx in ranked_indices:
        chunk, file_record, _ = valid_rows[idx]
        h_score = float(hybrid_scores[idx])
        s_score = float(sem_scores_norm[idx])
        k_score = float(kw_scores_norm[idx])

        # Combined highlighting
        highlights = compute_keyword_highlights(chunk.chunk_text, clean_query)
        sem_highlights = compute_semantic_highlights(chunk.chunk_text, query_emb, model)
        highlights.extend(sem_highlights)

        results.append(
            SearchResultItem(
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.chunk_text,
                file_id=file_record.id,
                original_filename=file_record.original_filename,
                similarity_score=round(h_score, 4),
                semantic_score=round(s_score, 4),
                keyword_score=round(k_score, 4),
                extension=file_record.extension,
                mime_type=file_record.mime_type,
                uploaded_at=file_record.uploaded_at,
                highlight_ranges=highlights,
            )
        )

    log_audit(
        db=db,
        user_id=user_id,
        action="hybrid_search",
        query=clean_query,
        file_id=file_id,
        details=f"Hybrid search: top_k={top_k}, file_id={file_id}, kw_w={norm_kw_w:.2f}, sem_w={norm_sem_w:.2f}, results={len(results)}",
    )

    return HybridSearchResponse(
        query=clean_query,
        search_mode="hybrid",
        file_id=file_id,
        keyword_weight=round(norm_kw_w, 4),
        semantic_weight=round(norm_sem_w, 4),
        total_results=len(results),
        results=results,
    )
