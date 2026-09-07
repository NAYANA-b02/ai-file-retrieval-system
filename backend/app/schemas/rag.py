from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CitationItem(BaseModel):
    file_id: int
    original_filename: str
    chunk_id: int
    chunk_index: int
    similarity_score: float
    snippet: str

    model_config = ConfigDict(from_attributes=True)


class RAGQuestionRequest(BaseModel):
    question: str = Field(..., description="User question for RAG")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of context chunks to retrieve (1-20)")


class RAGAnswerResponse(BaseModel):
    question: str
    answer: str
    citations: List[CitationItem]
    retrieval_metadata: Optional[Dict[str, Any]] = None
