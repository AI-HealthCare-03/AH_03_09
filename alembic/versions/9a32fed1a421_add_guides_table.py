"""add_guides_table

Revision ID: 9a32fed1a421
Revises: 763b49ebba4c
Create Date: 2026-06-05 14:23:10.824026

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9a32fed1a421"
down_revision: Union[str, Sequence[str], None] = "763b49ebba4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "guides",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("guide_id", sa.String(length=36), nullable=False),
        sa.Column("patient_id", sa.String(length=255), nullable=True),
        sa.Column("guide_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("feedback_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("guide_id"),
    )
    op.create_index("ix_guides_guide_id", "guides", ["guide_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_guides_guide_id", table_name="guides")
    op.drop_table("guides")
