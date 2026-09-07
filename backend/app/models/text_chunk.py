from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Text, LargeBinary, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class TextChunk(Base):
    __tablename__ = "text_chunks"
    __table_args__ = (
        UniqueConstraint("file_id", "chunk_index", name="uq_file_chunk_index"),
    )

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    embedding = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    file = relationship("File", back_populates="chunks", foreign_keys=[file_id])
