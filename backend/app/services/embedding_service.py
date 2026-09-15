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
BATCH_SIZE = 16        # FastEmbed batch size for bounded memory usage


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
    """Load the FastEmbed TextEmbedding model once and reuse it."""
    global _embedding_model
    if _embedding_model is None:
        model_name = settings.EMBEDDING_MODEL_NAME
        logger.info("FastEmbed TextEmbedding model loading started: %s", model_name)
        from fastembed import TextEmbedding
        _embedding_model = TextEmbedding(model_name=model_name)
        logger.info("FastEmbed TextEmbedding model loaded successfully: %s", model_name)
    return _embedding_model


def generate_embeddings(texts: List[str], batch_size: int = BATCH_SIZE) -> List[np.ndarray]:
    """
    Generate embeddings for a list of text strings using FastEmbed.
    Returns a list of numpy float32 arrays (384-dim for BAAI/bge-small-en-v1.5).
    """
    if not texts:
        return []
    model = _get_embedding_model()
    embeddings = model.embed(texts, batch_size=batch_size)
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

    - Skips files whose processing_status is not 'completed' or 'processing'
    - Skips files with empty / whitespace-only extracted_text
    - Deletes existing chunks first (idempotent / repeatable)
    - Sets processing_status to 'completed' and error_message to None on success
    - Sets processing_status to 'failed' on exception
    - Streams embeddings in small batches to keep memory usage bounded
    - Returns the number of chunks created, or None if skipped or failed

    Never raises; logs errors internally.
    """
    logger.info("process_chunking_and_embedding: started for file_id=%d", file_id)
    file_record = db.query(File).filter(File.id == file_id).first()
    if not file_record:
        logger.warning("process_chunking_and_embedding: file_id=%d not found", file_id)
        return None

    logger.info(
        "process_chunking_and_embedding: file_id=%d lookup status=%s, has_extracted_text=%s",
        file_id,
        file_record.processing_status,
        bool(file_record.extracted_text and file_record.extracted_text.strip()),
    )

    # Only process files with successfully extracted text (completed or processing)
    if file_record.processing_status not in ("completed", "processing"):
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
        logger.info("process_chunking_and_embedding: generated %d chunks for file_id=%d", len(chunks), file_id)
        if not chunks:
            file_record.text_chunk_count = 0
            db.commit()
            return 0

        # 3. Generate embeddings in small batches and persist TextChunk records
        logger.info("process_chunking_and_embedding: before embedding generation for file_id=%d (%d chunks)", file_id, len(chunks))
        model = _get_embedding_model()
        chunk_idx = 0
        for i in range(0, len(chunks), BATCH_SIZE):
            batch_chunks = chunks[i : i + BATCH_SIZE]
            batch_embeddings = model.embed(batch_chunks, batch_size=len(batch_chunks))
            for chunk_text_str, emb in zip(batch_chunks, batch_embeddings):
                text_chunk = TextChunk(
                    file_id=file_id,
                    chunk_index=chunk_idx,
                    chunk_text=chunk_text_str,
                    embedding=serialize_embedding(emb.astype(np.float32)),
                )
                db.add(text_chunk)
                chunk_idx += 1
            db.flush()

        logger.info("process_chunking_and_embedding: after embedding generation for file_id=%d", file_id)

        # 4. Update chunk count, processing_status, and clear error_message on file record
        file_record.text_chunk_count = len(chunks)
        file_record.processing_status = "completed"
        file_record.error_message = None
        logger.info("process_chunking_and_embedding: before database commit for file_id=%d", file_id)
        db.commit()
        logger.info(
            "process_chunking_and_embedding: after database commit for file_id=%d (status=%s, chunk_count=%d)",
            file_id,
            file_record.processing_status,
            file_record.text_chunk_count,
        )

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
