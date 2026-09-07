"""add_text_chunks_fts_gin_index

Revision ID: 99f975ef0c3e
Revises: 057114ca1473
Create Date: 2026-09-07 21:02:55.865320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99f975ef0c3e'
down_revision: Union[str, Sequence[str], None] = '057114ca1473'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_text_chunks_tsv ON text_chunks USING gin (to_tsvector('english', chunk_text));"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_text_chunks_tsv;")
