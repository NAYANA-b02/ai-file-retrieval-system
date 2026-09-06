from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class FileOut(BaseModel):
    id: int
    owner_id: int
    original_filename: str
    stored_filename: str
    extension: str
    mime_type: str
    size: int
    uploaded_at: datetime
    extracted_text: Optional[str] = None
    processing_status: str
    error_message: Optional[str] = None
    text_chunk_count: int

    model_config = ConfigDict(from_attributes=True)
