from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return (1-50)")


class SearchResultItem(BaseModel):
    chunk_id: int
    chunk_index: int
    chunk_text: str
    file_id: int
    original_filename: str
    similarity_score: float
    extension: Optional[str] = None
    mime_type: Optional[str] = None
    uploaded_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SemanticSearchResponse(BaseModel):
    query: str
    total_results: int
    results: List[SearchResultItem]
