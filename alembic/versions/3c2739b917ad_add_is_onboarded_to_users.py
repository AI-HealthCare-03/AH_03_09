"""add is_onboarded to users

Revision ID: 3c2739b917ad
Revises: 763b49ebba4c
Create Date: 2026-06-05 06:11:46.109728

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3c2739b917ad"
down_revision: Union[str, Sequence[str], None] = "763b49ebba4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_onboarded", sa.Boolean(), nullable=False, server_default=sa.text("false")))


def downgrade() -> None:
    op.drop_column("users", "is_onboarded")
