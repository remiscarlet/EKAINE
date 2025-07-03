"""Remove core.commodities.avg_price

Revision ID: e5a84707f2a0
Revises: 013ea109edbb
Create Date: 2025-07-02 16:19:31.792074

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5a84707f2a0"
down_revision: str | None = "013ea109edbb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("commodities", "avg_price", schema="core")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("commodities", sa.Column("avg_price", sa.SmallInteger(), nullable=True), schema="core")
