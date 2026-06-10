"""add embedding to drug_master

Revision ID: a2b3c4d5e6f7
Revises: 3c2739b917ad
Create Date: 2026-06-10
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "3c2739b917ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("ALTER TABLE drug_master ADD COLUMN IF NOT EXISTS embedding vector(1536)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_drug_master_embedding_ivfflat")
    op.execute("ALTER TABLE drug_master DROP COLUMN IF EXISTS embedding")
