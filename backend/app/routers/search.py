from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.search import (
    SemanticSearchRequest,
    SemanticSearchResponse,
    KeywordSearchRequest,
    KeywordSearchResponse,
    HybridSearchRequest,
    HybridSearchResponse,
)
from app.services.search_service import (
    execute_semantic_search,
    execute_keyword_search,
    execute_hybrid_search,
)

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


# ---------------------------------------------------------------------------
# Semantic Search Endpoints (Phase 6 preserved)
# ---------------------------------------------------------------------------
@router.post(
    "/semantic",
    response_model=SemanticSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic search over user documents (POST)",
)
def semantic_search_post(
    request: SemanticSearchRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    Execute semantic search via JSON body:
    - Requires session authentication
    - Encodes query via all-MiniLM-L6-v2
    - Scored by cosine similarity against chunks owned by the current user
    - Returns top-k most relevant chunks
    - Never exposes physical server filesystem paths
    """
    return execute_semantic_search(
        db=db,
        user_id=current_user.id,
        query=request.query,
        top_k=request.top_k,
    )


@router.get(
    "/semantic",
    response_model=SemanticSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic search over user documents (GET)",
)
def semantic_search_get(
    query: str = Query(..., description="Natural language search query"),
    top_k: int = Query(default=5, ge=1, le=50, description="Number of results (1-50)"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    Execute semantic search via query parameters:
    - Requires session authentication
    - Encodes query via all-MiniLM-L6-v2
    - Scored by cosine similarity against chunks owned by the current user
    - Returns top-k most relevant chunks
    """
    return execute_semantic_search(
        db=db,
        user_id=current_user.id,
        query=query,
        top_k=top_k,
    )


# ---------------------------------------------------------------------------
# Keyword Search Endpoints (Phase 7)
# ---------------------------------------------------------------------------
@router.post(
    "/keyword",
    response_model=KeywordSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Keyword search over user documents (POST)",
)
def keyword_search_post(
    request: KeywordSearchRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    Execute keyword search via JSON body:
    - Requires session authentication
    - Uses PostgreSQL-native Full-Text Search and exact term matching
    - Returns top-k most relevant chunks owned exclusively by the user
    """
    return execute_keyword_search(
        db=db,
        user_id=current_user.id,
        query=request.query,
        top_k=request.top_k,
    )


@router.get(
    "/keyword",
    response_model=KeywordSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Keyword search over user documents (GET)",
)
def keyword_search_get(
    query: str = Query(..., description="Keyword search query"),
    top_k: int = Query(default=5, ge=1, le=50, description="Number of results (1-50)"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    Execute keyword search via query parameters:
    - Requires session authentication
    - Uses PostgreSQL-native Full-Text Search and exact term matching
    - Returns top-k most relevant chunks owned exclusively by the user
    """
    return execute_keyword_search(
        db=db,
        user_id=current_user.id,
        query=query,
        top_k=top_k,
    )


# ---------------------------------------------------------------------------
# Hybrid Search Endpoints (Phase 7)
# ---------------------------------------------------------------------------
@router.post(
    "/hybrid",
    response_model=HybridSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Hybrid search combining keyword relevance and semantic similarity (POST)",
)
def hybrid_search_post(
    request: HybridSearchRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    Execute hybrid search via JSON body:
    - Requires session authentication
    - Combines dense semantic vector similarity and sparse keyword relevance
    - S_hybrid = (W_sem * S_sem_norm) + (W_kw * S_kw_norm)
    - Default weights: 0.6 semantic, 0.4 keyword
    - Returns top-k most relevant chunks owned exclusively by the user
    """
    return execute_hybrid_search(
        db=db,
        user_id=current_user.id,
        query=request.query,
        top_k=request.top_k,
        keyword_weight=request.keyword_weight,
        semantic_weight=request.semantic_weight,
    )


@router.get(
    "/hybrid",
    response_model=HybridSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Hybrid search combining keyword relevance and semantic similarity (GET)",
)
def hybrid_search_get(
    query: str = Query(..., description="Search query"),
    top_k: int = Query(default=5, ge=1, le=50, description="Number of results (1-50)"),
    keyword_weight: Optional[float] = Query(default=None, ge=0.0, le=1.0, description="Keyword weight"),
    semantic_weight: Optional[float] = Query(default=None, ge=0.0, le=1.0, description="Semantic weight"),
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    Execute hybrid search via query parameters:
    - Requires session authentication
    - Combines dense semantic vector similarity and sparse keyword relevance
    - Returns top-k most relevant chunks owned exclusively by the user
    """
    return execute_hybrid_search(
        db=db,
        user_id=current_user.id,
        query=query,
        top_k=top_k,
        keyword_weight=keyword_weight,
        semantic_weight=semantic_weight,
    )


# ---------------------------------------------------------------------------
# General Search Alias
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=HybridSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="General search endpoint (defaults to hybrid search)",
)
def search_post_alias(
    request: HybridSearchRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Convenience alias for /api/v1/search/hybrid."""
    return execute_hybrid_search(
        db=db,
        user_id=current_user.id,
        query=request.query,
        top_k=request.top_k,
        keyword_weight=request.keyword_weight,
        semantic_weight=request.semantic_weight,
    )
