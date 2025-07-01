"""Add pg_trgm and trigram indexes

Revision ID: 013ea109edbb
Revises: 47997637c6fa
Create Date: 2025-06-30 15:14:37.849547

"""

from typing import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013ea109edbb"
down_revision: str | None = "47997637c6fa"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # Systems
    op.execute("CREATE INDEX ix_core_systems_name_trgm " "ON core.systems USING GIN (lower(name) gin_trgm_ops)")

    # Bodies
    op.execute("CREATE INDEX ix_core_bodies_name_trgm " "ON core.bodies USING GIN (lower(name) gin_trgm_ops)")

    # Rings
    op.execute("CREATE INDEX ix_core_rings_name_trgm " "ON core.rings USING GIN (lower(name) gin_trgm_ops)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS core.ix_core_systems_name_trgm")
    op.execute("DROP INDEX IF EXISTS core.ix_core_bodies_name_trgm")
    op.execute("DROP INDEX IF EXISTS core.ix_core_rings_name_trgm")

    op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
