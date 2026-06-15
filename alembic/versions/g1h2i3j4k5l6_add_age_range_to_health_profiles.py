"""add age_range to health_profiles, remove birth_date

Revision ID: g1h2i3j4k5l6
Revises: f1a2b3c4d5e6
Create Date: 2026-06-16

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("health_profiles", sa.Column("age_range", sa.String(length=20), nullable=True))
    op.drop_column("health_profiles", "birth_date")


def downgrade() -> None:
    op.add_column("health_profiles", sa.Column("birth_date", sa.Date(), nullable=True))
    op.drop_column("health_profiles", "age_range")
