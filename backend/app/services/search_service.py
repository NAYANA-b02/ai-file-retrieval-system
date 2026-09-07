import logging
from typing import List, Optional
import numpy as np
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.models.file import File
from app.models.text_chunk import TextChunk
from app.schemas.search import (
    SearchResultItem,
    SemanticSearchResponse,
    KeywordSearchResponse,
    HybridSearchResponse,
)
from app.services.embedding_service import _get_embedding_model, deserialize_embedding
from app.services.audit_service import log_audit

logger = logging.getLogger(__name__)


def execute_semantic_search(
    db: DBSession,
    user_id: int,
    query: str,
    top_k: int = 5,
) -> SemanticSearchResponse:
    """
    Perform semantic search across document chunks belonging strictly to the user.

    - Reuses the all-MiniLM-L6-v2 model to encode the query.
    - Computes cosine similarity against all user-owned chunks.
    - Returns top-k most relevant chunks ordered by descending similarity score.
    - Enforces ownership: only returns chunks from files where file.owner_id == user_id.
    - Excludes internal filesystem paths and sensitive server details.
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

    rows = (
        db.query(TextChunk, File)
        .join(File, TextChunk.file_id == File.id)
        .filter(File.owner_id == user_id)
        .filter(File.processing_status == "completed")
        .all()
    )

    valid_rows = [(chunk, file_record) for chunk, file_record in rows if chunk.embedding]

    if not valid_rows:
        log_audit(
            db=db,
            user_id=user_id,
            action="semantic_search",
            query=clean_query,
            details=f"Semantic search: top_k={top_k}, results=0",
        )
        return SemanticSearchResponse(
            query=clean_query,
            search_mode="semantic",
            total_results=0,
            results=[],
        )

    model = _get_embedding_model()
    query_emb = model.encode(clean_query, convert_to_numpy=True).astype(np.float32)
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
            )
        )

    log_audit(
        db=db,
        user_id=user_id,
        action="semantic_search",
        query=clean_query,
        details=f"Semantic search: top_k={top_k}, results={len(results)}",
    )

    return SemanticSearchResponse(
        query=clean_query,
        search_mode="semantic",
        total_results=len(results),
        results=results,
    )


def execute_keyword_search(
    db: DBSession,
    user_id: int,
    query: str,
    top_k: int = 5,
) -> KeywordSearchResponse:
    """
    Perform keyword-based search over document chunks owned by the authenticated user.

    - Uses PostgreSQL-native Full-Text Search (ts_rank_cd over to_tsvector and plainto_tsquery).
    - Augments with exact token/phrase matching for exact term matches.
    - Normalizes scores into [0.0, 1.0].
    - Returns top-k most relevant chunks ordered by descending keyword score.
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

    # PostgreSQL FTS rank expression
    ts_vector = func.to_tsvector("english", TextChunk.chunk_text)
    ts_query = func.plainto_tsquery("english", clean_query)
    fts_rank_expr = func.ts_rank_cd(ts_vector, ts_query)

    rows = (
        db.query(TextChunk, File, fts_rank_expr.label("fts_rank"))
        .join(File, TextChunk.file_id == File.id)
        .filter(File.owner_id == user_id)
        .filter(File.processing_status == "completed")
        .all()
    )

    if not rows:
        log_audit(
            db=db,
            user_id=user_id,
            action="keyword_search",
            query=clean_query,
            details=f"Keyword search: top_k={top_k}, results=0",
        )
        return KeywordSearchResponse(
            query=clean_query,
            search_mode="keyword",
            total_results=0,
            results=[],
        )

    # Compute keyword relevance score
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
            details=f"Keyword search: top_k={top_k}, results=0",
        )
        return KeywordSearchResponse(
            query=clean_query,
            search_mode="keyword",
            total_results=0,
            results=[],
        )

    # Sort descending by raw keyword score
    scored_items.sort(key=lambda x: x[0], reverse=True)
    max_score = scored_items[0][0]

    top_items = scored_items[:top_k]
    results: List[SearchResultItem] = []
    for raw_score, chunk, file_record in top_items:
        normalized_score = round(raw_score / max_score, 4) if max_score > 0 else 0.0
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
            )
        )

    log_audit(
        db=db,
        user_id=user_id,
        action="keyword_search",
        query=clean_query,
        details=f"Keyword search: top_k={top_k}, results={len(results)}",
    )

    return KeywordSearchResponse(
        query=clean_query,
        search_mode="keyword",
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
) -> HybridSearchResponse:
    """
    Perform hybrid search combining keyword relevance and semantic similarity.

    - Formula: S_hybrid = (W_sem * S_sem_norm) + (W_kw * S_kw_norm)
    - Default weights from config: W_sem = 0.6, W_kw = 0.4.
    - S_sem_norm: Cosine similarity clamped to [0.0, 1.0].
    - S_kw_norm: PostgreSQL FTS + exact token/phrase matching scaled into [0.0, 1.0].
    - Combined score is deterministic and bounded in [0.0, 1.0].
    - Enforces ownership: only returns chunks from files where file.owner_id == user_id.
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

    kw_w = settings.KEYWORD_SEARCH_WEIGHT if keyword_weight is None else keyword_weight
    sem_w = settings.SEMANTIC_SEARCH_WEIGHT if semantic_weight is None else semantic_weight

    if kw_w < 0.0 or sem_w < 0.0 or (kw_w + sem_w) <= 0.0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Weights must be non-negative and sum to greater than 0",
        )

    # Normalize weights so they sum to 1.0
    total_w = kw_w + sem_w
    norm_kw_w = kw_w / total_w
    norm_sem_w = sem_w / total_w

    # Retrieve chunks with FTS rank and verify embeddings
    ts_vector = func.to_tsvector("english", TextChunk.chunk_text)
    ts_query = func.plainto_tsquery("english", clean_query)
    fts_rank_expr = func.ts_rank_cd(ts_vector, ts_query)

    rows = (
        db.query(TextChunk, File, fts_rank_expr.label("fts_rank"))
        .join(File, TextChunk.file_id == File.id)
        .filter(File.owner_id == user_id)
        .filter(File.processing_status == "completed")
        .all()
    )

    valid_rows = [(chunk, file_record, float(fts_rank or 0.0)) for chunk, file_record, fts_rank in rows if chunk.embedding]

    if not valid_rows:
        log_audit(
            db=db,
            user_id=user_id,
            action="hybrid_search",
            query=clean_query,
            details=f"Hybrid search: top_k={top_k}, results=0",
        )
        return HybridSearchResponse(
            query=clean_query,
            search_mode="hybrid",
            keyword_weight=round(norm_kw_w, 4),
            semantic_weight=round(norm_sem_w, 4),
            total_results=0,
            results=[],
        )

    # 1. Semantic Scoring
    model = _get_embedding_model()
    query_emb = model.encode(clean_query, convert_to_numpy=True).astype(np.float32)
    query_norm = np.linalg.norm(query_emb)
    if query_norm > 0:
        query_emb = query_emb / query_norm

    chunk_embeddings = np.vstack([deserialize_embedding(chunk.embedding) for chunk, _, _ in valid_rows])
    chunk_norms = np.linalg.norm(chunk_embeddings, axis=1, keepdims=True)
    chunk_norms[chunk_norms == 0] = 1e-10
    normalized_chunks = chunk_embeddings / chunk_norms

    raw_sem_scores = np.dot(normalized_chunks, query_emb)
    # Clamp negative cosine similarities to 0.0 for hybrid combination
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
            )
        )

    log_audit(
        db=db,
        user_id=user_id,
        action="hybrid_search",
        query=clean_query,
        details=f"Hybrid search: top_k={top_k}, kw_w={norm_kw_w:.2f}, sem_w={norm_sem_w:.2f}, results={len(results)}",
    )

    return HybridSearchResponse(
        query=clean_query,
        search_mode="hybrid",
        keyword_weight=round(norm_kw_w, 4),
        semantic_weight=round(norm_sem_w, 4),
        total_results=len(results),
        results=results,
    )
