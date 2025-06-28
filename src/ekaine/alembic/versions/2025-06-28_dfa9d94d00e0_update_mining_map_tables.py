"""Modify mining map tables

Revision ID: dfa9d94d00e0
Revises: d23e4d974afb
Create Date: 2025-06-28 13:55:41.390861

"""

from typing import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dfa9d94d00e0"
down_revision: str | None = "d23e4d974afb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    # Doesn't seem to add it automatically for some reason?
    op.execute("ALTER TABLE core.mining_maps DROP CONSTRAINT IF EXISTS _mining_map_uc;")
    op.execute("ALTER TABLE core.mining_maps ADD CONSTRAINT _mining_map_uc UNIQUE (system_id, body_id, ring_id, name)")
    op.execute("ALTER TABLE core.mining_maps ALTER COLUMN rock_count DROP NOT NULL;")
    op.execute("ALTER TABLE core.mining_maps ALTER COLUMN approximate_merits_solo DROP NOT NULL;")
    op.execute("ALTER TABLE core.mining_map_commodities ALTER COLUMN approximate_tonnage_solo DROP NOT NULL;")


def downgrade() -> None:
    """Downgrade schema."""

    op.execute("ALTER TABLE core.mining_maps DROP CONSTRAINT IF EXISTS _mining_map_uc")
    op.execute("ALTER TABLE core.mining_maps ALTER COLUMN rock_count SET NOT NULL;")
    op.execute("ALTER TABLE core.mining_maps ALTER COLUMN approximate_merits_solo SET NOT NULL;")
    op.execute("ALTER TABLE core.mining_map_commodities ALTER COLUMN approximate_tonnage_solo SET NOT NULL;")
