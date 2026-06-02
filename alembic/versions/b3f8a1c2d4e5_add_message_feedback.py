"""add message feedback

Revision ID: b3f8a1c2d4e5
Revises: 7162fbb2b310
Create Date: 2026-05-27 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3f8a1c2d4e5"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("feedback", sa.String(10), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_messages", "feedback")
