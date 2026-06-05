"""add_is_db_matched_to_medications

Revision ID: 763b49ebba4c
Revises: 6eeb06bb552d
Create Date: 2026-06-04 09:01:59.242901

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "763b49ebba4c"
down_revision: Union[str, Sequence[str], None] = "6eeb06bb552d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("medications", sa.Column("is_db_matched", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("medications", "is_db_matched")
