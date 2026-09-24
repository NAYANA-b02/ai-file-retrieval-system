"""add_document_visuals_table

Revision ID: a1b2c3d4e5f6
Revises: 99f975ef0c3e
Create Date: 2026-09-23 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '99f975ef0c3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'document_visuals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('visual_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('visual_type', sa.String(length=50), nullable=False, server_default='embedded_image'),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False, server_default='image/png'),
        sa.Column('caption', sa.String(length=500), nullable=True),
        sa.Column('context_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_document_visuals_id'), 'document_visuals', ['id'], unique=False)
    op.create_index(op.f('ix_document_visuals_file_id'), 'document_visuals', ['file_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_document_visuals_file_id'), table_name='document_visuals')
    op.drop_index(op.f('ix_document_visuals_id'), table_name='document_visuals')
    op.drop_table('document_visuals')
