"""add_text_chunks_table

Revision ID: 057114ca1473
Revises: 77941673a99c
Create Date: 2026-09-07 20:24:32.396385

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '057114ca1473'
down_revision: Union[str, Sequence[str], None] = '77941673a99c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('text_chunks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('file_id', sa.Integer(), nullable=False),
    sa.Column('chunk_index', sa.Integer(), nullable=False),
    sa.Column('chunk_text', sa.Text(), nullable=False),
    sa.Column('embedding', sa.LargeBinary(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('file_id', 'chunk_index', name='uq_file_chunk_index')
    )
    op.create_index(op.f('ix_text_chunks_file_id'), 'text_chunks', ['file_id'], unique=False)
    op.create_index(op.f('ix_text_chunks_id'), 'text_chunks', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_text_chunks_id'), table_name='text_chunks')
    op.drop_index(op.f('ix_text_chunks_file_id'), table_name='text_chunks')
    op.drop_table('text_chunks')
