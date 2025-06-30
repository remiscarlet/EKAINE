"""Update views and add indexes

Revision ID: df38aedf45b0
Revises: 75792b281582
Create Date: 2025-06-22 14:05:29.435523

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

from ekaine.common.constants import SQL_DIR

views_sql_dir = SQL_DIR / "views"
functions_sql_dir = SQL_DIR / "functions"


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
    with open(views_sql_dir / "archives" / "derived_hotspot_ring_view_v3.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "archives" / "derived_acquisition_routes_v2.sql") as f:
        op.execute(f.read())

    # New views
    with open(views_sql_dir / "m_derived_commodity_prices_view_v1.sql") as f:
        op.execute(f.read())

    # New function
    with open(functions_sql_dir / "derived_get_rings_in_system_v1.sql") as f:
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

    # Add columns
    op.add_column(
        "mining_maps",
        sa.Column(
            "ring_id",
            sa.Integer(),
            sa.ForeignKey("core.rings.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        schema="core",
    )
    op.drop_column("mining_maps", "hotspot_id", schema="core")

    # Materialized view refresh cron
    every = 6  # hours
    op.execute(
        "SELECT cron.schedule('refresh_derived_commodity_prices_view', "
        f"'0 */{every} * * *', $$REFRESH MATERIALIZED VIEW CONCURRENTLY derived.commodity_prices_view;$$);"
    )


def downgrade() -> None:
    """Downgrade schema."""

    # Stop materialized view refresh cron
    op.execute("SELECT cron.unschedule('refresh_derived_commodity_prices_view')")

    # Drop new column/add old one
    op.add_column(
        "mining_maps",
        sa.Column(
            "hotspot_id",
            sa.Integer(),
            nullable=True,
            index=True,
        ),
        schema="core",
    )
    op.drop_column("mining_maps", "ring_id", schema="core")

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
    with open(views_sql_dir / "archives" / "derived_acquisition_routes_v2.sql") as f:
        op.execute(f.read())

    # Drop new view
    op.execute("drop view if exists derived.commodity_prices_view")

    # Drop new function
    op.execute("drop function if exists derived.get_rings_in_system")
