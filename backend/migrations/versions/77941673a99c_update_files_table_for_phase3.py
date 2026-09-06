"""update_files_table_for_phase3

Revision ID: 77941673a99c
Revises: 4921cbcc74a3
Create Date: 2026-09-06 18:36:54.524812

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '77941673a99c'
down_revision: Union[str, Sequence[str], None] = '4921cbcc74a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Check existing columns in files table dynamically or alter safely
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_cols = [c["name"] for c in inspector.get_columns("files")]

    if "owner_id" not in existing_cols and "user_id" in existing_cols:
        op.alter_column('files', 'user_id', new_column_name='owner_id')
    elif "owner_id" not in existing_cols:
        op.add_column('files', sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False))

    if "original_filename" not in existing_cols and "filename" in existing_cols:
        op.alter_column('files', 'filename', new_column_name='original_filename')
    elif "original_filename" not in existing_cols:
        op.add_column('files', sa.Column('original_filename', sa.String(length=255), nullable=False))

    if "mime_type" not in existing_cols and "content_type" in existing_cols:
        op.alter_column('files', 'content_type', new_column_name='mime_type')
    elif "mime_type" not in existing_cols:
        op.add_column('files', sa.Column('mime_type', sa.String(length=100), nullable=False))

    if "size" not in existing_cols and "file_size" in existing_cols:
        op.alter_column('files', 'file_size', new_column_name='size')
    elif "size" not in existing_cols:
        op.add_column('files', sa.Column('size', sa.Integer(), nullable=False))

    if "uploaded_at" not in existing_cols and "created_at" in existing_cols:
        op.alter_column('files', 'created_at', new_column_name='uploaded_at')
    elif "uploaded_at" not in existing_cols:
        op.add_column('files', sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False))

    if "processing_status" not in existing_cols and "status" in existing_cols:
        op.alter_column('files', 'status', new_column_name='processing_status')
    elif "processing_status" not in existing_cols:
        op.add_column('files', sa.Column('processing_status', sa.String(length=50), nullable=False, server_default='uploaded'))

    if "extension" not in existing_cols:
        op.add_column('files', sa.Column('extension', sa.String(length=20), nullable=False, server_default=''))

    if "extracted_text" not in existing_cols:
        op.add_column('files', sa.Column('extracted_text', sa.Text(), nullable=True))

    if "error_message" not in existing_cols:
        op.add_column('files', sa.Column('error_message', sa.String(length=1000), nullable=True))

    if "text_chunk_count" not in existing_cols:
        op.add_column('files', sa.Column('text_chunk_count', sa.Integer(), nullable=False, server_default='0'))

    # Drop old file_hash if it exists and is not in model, or make it nullable
    if "file_hash" in existing_cols:
        op.alter_column('files', 'file_hash', nullable=True)

    # Ensure index exists on extension and processing_status
    op.create_index(op.f('ix_files_extension'), 'files', ['extension'], unique=False, if_not_exists=True)
    op.create_index(op.f('ix_files_processing_status'), 'files', ['processing_status'], unique=False, if_not_exists=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_files_processing_status'), table_name='files')
    op.drop_index(op.f('ix_files_extension'), table_name='files')
    op.drop_column('files', 'text_chunk_count')
    op.drop_column('files', 'error_message')
    op.drop_column('files', 'extracted_text')
    op.drop_column('files', 'extension')
    op.alter_column('files', 'processing_status', new_column_name='status')
    op.alter_column('files', 'uploaded_at', new_column_name='created_at')
    op.alter_column('files', 'size', new_column_name='file_size')
    op.alter_column('files', 'mime_type', new_column_name='content_type')
    op.alter_column('files', 'original_filename', new_column_name='filename')
    op.alter_column('files', 'owner_id', new_column_name='user_id')
