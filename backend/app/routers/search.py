from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.search import SemanticSearchRequest, SemanticSearchResponse
from app.services.search_service import execute_semantic_search

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


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


@router.post(
    "",
    response_model=SemanticSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="General search endpoint (defaults to semantic search)",
)
def search_post_alias(
    request: SemanticSearchRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """Convenience alias for /api/v1/search/semantic."""
    return execute_semantic_search(
        db=db,
        user_id=current_user.id,
        query=request.query,
        top_k=request.top_k,
    )
