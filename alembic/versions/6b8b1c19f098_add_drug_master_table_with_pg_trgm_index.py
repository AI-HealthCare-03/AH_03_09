"""add drug_master table with pg_trgm index

Revision ID: 6b8b1c19f098
Revises: d1e2f3a4b5c6
Create Date: 2026-05-27 02:38:37.082421

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6b8b1c19f098"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "drug_master",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("item_name", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_drug_master_item_name"), "drug_master", ["item_name"], unique=False)
    op.create_index(
        "ix_drug_master_item_name_trgm",
        "drug_master",
        ["item_name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"item_name": "gin_trgm_ops"},
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_drug_master_item_name_trgm", table_name="drug_master")
    op.drop_index(op.f("ix_drug_master_item_name"), table_name="drug_master")
    op.drop_table("drug_master")
