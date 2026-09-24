from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session as DBSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.rag import RAGQuestionRequest, RAGAnswerResponse
from app.services.rag_service import execute_rag

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])


@router.post(
    "/ask",
    response_model=RAGAnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question grounded in user's documents (RAG)",
)
def ask_question(
    request: RAGQuestionRequest,
    current_user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """
    Execute grounded RAG for authenticated user:
    - Retrieves user-owned relevant document chunks via hybrid search
    - Formats chunks into an untrusted-data context with prompt injection defenses
    - Queries the local Ollama LLM
    - Returns grounded answer with programmatic citations to source chunks
    - Never exposes physical server filesystem paths
    """
    return execute_rag(
        db=db,
        user_id=current_user.id,
        question=request.question,
        top_k=request.top_k,
        file_id=request.file_id,
    )

