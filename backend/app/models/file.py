from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), unique=True, nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    extension = Column(String(20), nullable=False, index=True)
    mime_type = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    extracted_text = Column(Text, nullable=True)
    processing_status = Column(String(50), default="uploaded", nullable=False, index=True)
    error_message = Column(String(1000), nullable=True)
    text_chunk_count = Column(Integer, default=0, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="files", foreign_keys=[owner_id])
    user = relationship("User", back_populates="files", foreign_keys=[owner_id], overlaps="owner")
    chunks = relationship("TextChunk", back_populates="file", cascade="all, delete-orphan")

    # Compatibility aliases for any existing references
    @property
    def user_id(self):
        return self.owner_id

    @user_id.setter
    def user_id(self, val):
        self.owner_id = val

    @property
    def filename(self):
        return self.original_filename

    @filename.setter
    def filename(self, val):
        self.original_filename = val

    @property
    def content_type(self):
        return self.mime_type

    @content_type.setter
    def content_type(self, val):
        self.mime_type = val

    @property
    def file_size(self):
        return self.size

    @file_size.setter
    def file_size(self, val):
        self.size = val

    @property
    def status(self):
        return self.processing_status

    @status.setter
    def status(self, val):
        self.processing_status = val

    @property
    def created_at(self):
        return self.uploaded_at

    @created_at.setter
    def created_at(self, val):
        self.uploaded_at = val
