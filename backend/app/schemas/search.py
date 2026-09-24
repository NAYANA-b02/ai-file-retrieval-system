from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class HighlightRange(BaseModel):
    start: int
    end: int
    type: str = "keyword"  # "keyword" or "semantic"


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return (1-50)")
    file_id: Optional[int] = Field(default=None, description="Optional file ID to restrict search to a single document")


class KeywordSearchRequest(BaseModel):
    query: str = Field(..., description="Keyword search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return (1-50)")
    file_id: Optional[int] = Field(default=None, description="Optional file ID to restrict search to a single document")


class HybridSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to return (1-50)")
    file_id: Optional[int] = Field(default=None, description="Optional file ID to restrict search to a single document")
    keyword_weight: Optional[float] = Field(default=0.4, ge=0.0, le=1.0, description="Weight for keyword relevance (0.0 to 1.0)")
    semantic_weight: Optional[float] = Field(default=0.6, ge=0.0, le=1.0, description="Weight for semantic similarity (0.0 to 1.0)")


class SearchResultItem(BaseModel):
    chunk_id: int
    chunk_index: int
    chunk_text: str
    file_id: int
    original_filename: str
    similarity_score: float
    semantic_score: Optional[float] = None
    keyword_score: Optional[float] = None
    extension: Optional[str] = None
    mime_type: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    highlight_ranges: List[HighlightRange] = Field(default_factory=list)
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    page_number: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class SemanticSearchResponse(BaseModel):
    query: str
    search_mode: str = "semantic"
    file_id: Optional[int] = None
    total_results: int
    results: List[SearchResultItem]


class KeywordSearchResponse(BaseModel):
    query: str
    search_mode: str = "keyword"
    file_id: Optional[int] = None
    total_results: int
    results: List[SearchResultItem]


class HybridSearchResponse(BaseModel):
    query: str
    search_mode: str = "hybrid"
    file_id: Optional[int] = None
    keyword_weight: float = 0.4
    semantic_weight: float = 0.6
    total_results: int
    results: List[SearchResultItem]
