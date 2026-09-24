from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class DocumentVisual(Base):
    __tablename__ = "document_visuals"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    visual_index = Column(Integer, default=0, nullable=False)
    page_number = Column(Integer, nullable=True)
    visual_type = Column(String(50), default="embedded_image", nullable=False)  # embedded_image, page_render, uploaded_image
    storage_path = Column(String(500), nullable=False)
    mime_type = Column(String(100), default="image/png", nullable=False)
    caption = Column(String(500), nullable=True)
    context_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationship to File
    file = relationship("File", back_populates="visuals")
