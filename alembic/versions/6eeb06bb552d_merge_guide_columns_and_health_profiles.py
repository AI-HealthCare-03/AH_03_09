"""merge guide columns and health profiles

Revision ID: 6eeb06bb552d
Revises: e1f2a3b4c5d6, 588eaa5d1567
Create Date: 2026-06-04 06:25:27.189090

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6eeb06bb552d"
down_revision: Union[str, Sequence[str], None] = ("e1f2a3b4c5d6", "588eaa5d1567")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
