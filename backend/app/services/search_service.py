import logging
from typing import List
import numpy as np
from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.models.file import File
from app.models.text_chunk import TextChunk
from app.schemas.search import SearchResultItem, SemanticSearchResponse
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
    # 1. Validate query string
    if not query or not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty or whitespace only",
        )

    clean_query = query.strip()

    # 2. Validate top_k parameter
    if top_k < 1 or top_k > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="top_k must be between 1 and 50",
        )

    # 3. Retrieve user-owned document chunks with completed processing status
    rows = (
        db.query(TextChunk, File)
        .join(File, TextChunk.file_id == File.id)
        .filter(File.owner_id == user_id)
        .filter(File.processing_status == "completed")
        .all()
    )

    # Filter for chunks with valid binary embeddings
    valid_rows = [(chunk, file_record) for chunk, file_record in rows if chunk.embedding]

    if not valid_rows:
        # User has no chunks or no completed files with embeddings
        log_audit(
            db=db,
            user_id=user_id,
            action="semantic_search",
            query=clean_query,
            details=f"Semantic search: top_k={top_k}, results=0",
        )
        return SemanticSearchResponse(
            query=clean_query,
            total_results=0,
            results=[],
        )

    # 4. Generate normalized query embedding
    model = _get_embedding_model()
    query_emb = model.encode(clean_query, convert_to_numpy=True).astype(np.float32)
    query_norm = np.linalg.norm(query_emb)
    if query_norm > 0:
        query_emb = query_emb / query_norm

    # 5. Vectorized Cosine Similarity calculation
    chunk_embeddings = np.vstack([deserialize_embedding(chunk.embedding) for chunk, _ in valid_rows])
    chunk_norms = np.linalg.norm(chunk_embeddings, axis=1, keepdims=True)
    chunk_norms[chunk_norms == 0] = 1e-10
    normalized_chunks = chunk_embeddings / chunk_norms

    # Dot product with normalized vectors gives cosine similarity
    similarity_scores = np.dot(normalized_chunks, query_emb)

    # 6. Rank by descending similarity
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
                extension=file_record.extension,
                mime_type=file_record.mime_type,
                uploaded_at=file_record.uploaded_at,
            )
        )

    # 7. Audit log
    log_audit(
        db=db,
        user_id=user_id,
        action="semantic_search",
        query=clean_query,
        details=f"Semantic search: top_k={top_k}, results={len(results)}",
    )

    return SemanticSearchResponse(
        query=clean_query,
        total_results=len(results),
        results=results,
    )
