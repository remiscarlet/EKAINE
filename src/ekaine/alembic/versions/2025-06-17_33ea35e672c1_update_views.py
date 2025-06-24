"""Update views

Revision ID: 33ea35e672c1
Revises: 2086129b5566
Create Date: 2025-06-17 16:49:05.488484

Updates:
- derived.hotspot_ring_view v1 -> v2
"""

from typing import Sequence

from alembic import op

from ekaine.common.constants import SQL_DIR

views_sql_dir = SQL_DIR / "views"


# revision identifiers, used by Alembic.
revision: str = "33ea35e672c1"
down_revision: str | None = "2086129b5566"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Need to drop acquisition_routes first as it depends on hotspot_ring_view

    op.execute("drop view if exists derived.acquisition_routes")
    op.execute("drop view if exists derived.hotspot_ring_view")

    with open(views_sql_dir / "archives" / "derived_hotspot_ring_view_v2.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "derived_acquisition_routes_v2.sql") as f:
        op.execute(f.read())


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("drop view if exists derived.acquisition_routes")
    op.execute("drop view if exists derived.station_commodities_view")

    with open(views_sql_dir / "archives" / "derived_hotspot_ring_view_v1.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "derived_acquisition_routes_v2.sql") as f:
        op.execute(f.read())
