"""Update views and add indexes

Revision ID: df38aedf45b0
Revises: 75792b281582
Create Date: 2025-06-22 14:05:29.435523

"""

from typing import Sequence

from alembic import op

from ekaine.common.constants import SQL_DIR

views_sql_dir = SQL_DIR / "views"


# revision identifiers, used by Alembic.
revision: str = "df38aedf45b0"
down_revision: str | None = "75792b281582"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Update views
    op.execute("drop view if exists derived.acquisition_routes")
    op.execute("drop view if exists derived.hotspot_ring_view")
    op.execute("drop view if exists derived.station_commodities_view")

    with open(views_sql_dir / "derived_station_commodities_view_v3.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "derived_hotspot_ring_view_v3.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "derived_acquisition_routes_v2.sql") as f:
        op.execute(f.read())

    # Add indexes
    op.create_index(
        op.f("ix_core_market_commodities_supplydemand_updated_at"),
        "market_commodities",
        ["updated_at", "supply", "demand"],
        unique=False,
        schema="core",
    )
    op.create_index(
        op.f("ix_core_stations_owner_id_type"),
        "stations",
        ["owner_id", "owner_type"],
        unique=False,
        schema="core",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop new indexes
    op.drop_index("ix_core_market_commodities_supplydemand_updated_at", "market_commodities", schema="core")
    op.drop_index("ix_core_stations_owner_id_type", "stations", schema="core")

    # Downgrade views
    op.execute("drop view if exists derived.acquisition_routes")
    op.execute("drop view if exists derived.hotspot_ring_view")
    op.execute("drop view if exists derived.station_commodities_view")

    with open(views_sql_dir / "archives" / "derived_station_commodities_view_v2.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "archives" / "derived_hotspot_ring_view_v2.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "derived_acquisition_routes_v2.sql") as f:
        op.execute(f.read())
