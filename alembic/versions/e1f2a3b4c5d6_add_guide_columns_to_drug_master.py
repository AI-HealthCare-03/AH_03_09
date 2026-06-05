"""add guide columns to drug_master

Revision ID: e1f2a3b4c5d6
Revises: 6b8b1c19f098
Create Date: 2026-06-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "6b8b1c19f098"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("drug_master", sa.Column("dosage", sa.Text(), nullable=True))
    op.add_column("drug_master", sa.Column("cautions", sa.Text(), nullable=True))
    op.add_column("drug_master", sa.Column("side_effects", sa.Text(), nullable=True))
    op.add_column("drug_master", sa.Column("storage", sa.Text(), nullable=True))
    op.add_column("drug_master", sa.Column("etc_otc_code", sa.String(length=20), nullable=True))
    op.add_column("drug_master", sa.Column("source", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("drug_master", "source")
    op.drop_column("drug_master", "etc_otc_code")
    op.drop_column("drug_master", "storage")
    op.drop_column("drug_master", "side_effects")
    op.drop_column("drug_master", "cautions")
    op.drop_column("drug_master", "dosage")
