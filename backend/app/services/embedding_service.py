import logging
from typing import List, Optional

import numpy as np
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.models.file import File
from app.models.text_chunk import TextChunk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chunking configuration
# ---------------------------------------------------------------------------
CHUNK_SIZE = 500       # characters per chunk
CHUNK_OVERLAP = 50     # overlap between consecutive chunks


def chunk_text(text: str) -> List[str]:
    """
    Split text into fixed-size character chunks with overlap.

    Deterministic: same text always produces the same chunks.
    Empty / whitespace-only text returns an empty list.
    """
    if not text or not text.strip():
        return []

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


# ---------------------------------------------------------------------------
# Embedding model (lazy singleton)
# ---------------------------------------------------------------------------
_embedding_model = None


def _get_embedding_model():
    """Load the sentence-transformers model once and reuse it."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    return _embedding_model


def generate_embeddings(texts: List[str]) -> List[np.ndarray]:
    """
    Generate embeddings for a list of text strings.
    Returns a list of numpy float32 arrays (384-dim for all-MiniLM-L6-v2).
    """
    model = _get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return [emb.astype(np.float32) for emb in embeddings]


def serialize_embedding(embedding: np.ndarray) -> bytes:
    """Serialize a numpy float32 array to bytes for DB storage."""
    return embedding.tobytes()


def deserialize_embedding(data: bytes) -> np.ndarray:
    """Deserialize bytes back to a numpy float32 array."""
    return np.frombuffer(data, dtype=np.float32)


# ---------------------------------------------------------------------------
# Main processing function
# ---------------------------------------------------------------------------
def process_chunking_and_embedding(db: DBSession, file_id: int) -> Optional[int]:
    """
    Chunk the extracted text of a file and generate embeddings.

    - Skips files whose processing_status is not 'completed'
    - Skips files with empty / whitespace-only extracted_text
    - Deletes existing chunks first (idempotent / repeatable)
    - Returns the number of chunks created, or None if skipped

    Never raises; logs errors internally.
    """
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        logger.warning("process_chunking_and_embedding: file_id=%d not found", file_id)
        return None

    # Only process files with successfully extracted text
    if file_record.processing_status != "completed":
        logger.info(
            "Skipping chunking for file_id=%d (status=%s)",
            file_id, file_record.processing_status,
        )
        return None

    if not file_record.extracted_text or not file_record.extracted_text.strip():
        logger.info("Skipping chunking for file_id=%d (empty extracted_text)", file_id)
        file_record.text_chunk_count = 0
        db.commit()
        return 0

    try:
        # 1. Delete existing chunks (makes processing repeatable)
        db.query(TextChunk).filter(TextChunk.file_id == file_id).delete()
        db.flush()

        # 2. Chunk the text
        chunks = chunk_text(file_record.extracted_text)
        if not chunks:
            file_record.text_chunk_count = 0
            db.commit()
            return 0

        # 3. Generate embeddings in batch
        embeddings = generate_embeddings(chunks)

        # 4. Create TextChunk records
        for idx, (chunk_text_str, embedding) in enumerate(zip(chunks, embeddings)):
            text_chunk = TextChunk(
                file_id=file_id,
                chunk_index=idx,
                chunk_text=chunk_text_str,
                embedding=serialize_embedding(embedding),
            )
            db.add(text_chunk)

        # 5. Update chunk count on file record
        file_record.text_chunk_count = len(chunks)
        db.commit()

        logger.info(
            "Created %d chunks with embeddings for file_id=%d",
            len(chunks), file_id,
        )
        return len(chunks)

    except Exception as e:
        db.rollback()
        logger.exception(
            "Chunking/embedding failed for file_id=%d: %s", file_id, e,
        )
        file_record = db.query(File).filter(File.id == file_id).first()
        if file_record:
            file_record.processing_status = "failed"
            file_record.text_chunk_count = 0
            file_record.error_message = f"Text chunking and embedding failed: {type(e).__name__}"
            try:
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("Failed to commit failure status for file_id=%d", file_id)
        return None
