"""Add indexes and materialize views

Revision ID: 2ded584f2cc5
Revises: 0b35f9d0307b
Create Date: 2025-06-27 17:40:30.257088

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

from ekaine.common.constants import SQL_DIR

views_sql_dir = SQL_DIR / "views"

# revision identifiers, used by Alembic.
revision: str = "2ded584f2cc5"
down_revision: str | None = "0b35f9d0307b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new indexes
    op.create_index(
        op.f("ix_core_systems_cp_p_state_date"),
        "systems",
        ["controlling_power", "power_state", "date"],
        unique=False,
        schema="core",
        if_not_exists=True,
    )
    op.create_index(
        op.f("ix_core_systems_powers"),
        "systems",
        ["powers"],
        postgresql_using="gin",
        unique=False,
        schema="core",
        if_not_exists=True,
    )
    op.create_index(
        op.f("ix_core_systems_p_state_date"),
        "systems",
        ["power_state", "date"],
        unique=False,
        schema="core",
        if_not_exists=True,
    )
    op.create_index(
        op.f("ix_core_market_commodities_nonzero_supplydemand_updated_at"),
        "market_commodities",
        ["station_id", "commodity_sym", "updated_at"],
        postgresql_where=sa.text("supply>0 or demand>0"),
        unique=False,
        schema="core",
        if_not_exists=True,
    )

    # Update views
    op.execute("drop view if exists derived.acquisition_routes")
    op.execute("drop view if exists derived.hotspot_ring_view")
    op.execute("drop view if exists derived.station_commodities_view")
    op.execute("drop view if exists derived.resolved_stations_view")

    with open(views_sql_dir / "derived_resolved_stations_view_v2.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "derived_station_commodities_view_v3.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "derived_hotspot_ring_view_v4.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "derived_acquisition_routes_v3.sql") as f:
        op.execute(f.read())

    # New views
    with open(views_sql_dir / "derived_average_ring_metadata_view_v1.sql") as f:
        op.execute(f.read())

    # Materialized view refresh cron
    every = 10  # minutes
    op.execute(
        "SELECT cron.schedule('refresh_derived_acquisition_routes', "
        f"'0-59/{every} * * * *', $$REFRESH MATERIALIZED VIEW CONCURRENTLY derived.acquisition_routes;$$);"
    )
    op.execute(
        "SELECT cron.schedule('refresh_derived_hotspot_ring_view', "
        f"'2-59/{every} * * * *', $$REFRESH MATERIALIZED VIEW CONCURRENTLY derived.hotspot_ring_view;$$);"
    )
    op.execute(
        "SELECT cron.schedule('refresh_derived_resolved_stations_view', "
        f"'4-59/{every} * * * *', $$REFRESH MATERIALIZED VIEW CONCURRENTLY derived.resolved_stations_view;$$);"
    )

    # Once a day at midnight
    op.execute(
        "SELECT cron.schedule('refresh_derived_average_ring_metadata_view', "
        "'0 0 * * *', $$REFRESH MATERIALIZED VIEW CONCURRENTLY derived.average_ring_metadata_view;$$);"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop crons
    op.execute("SELECT cron.unschedule('refresh_derived_average_ring_metadata_view')")
    op.execute("SELECT cron.unschedule('refresh_derived_resolved_stations_view')")
    op.execute("SELECT cron.unschedule('refresh_derived_hotspot_ring_view')")
    op.execute("SELECT cron.unschedule('refresh_derived_acquisition_routes')")

    # Downgrade views
    op.execute("drop materialized view if exists derived.acquisition_routes")
    op.execute("drop materialized view if exists derived.hotspot_ring_view")
    op.execute("drop view if exists derived.station_commodities_view")
    op.execute("drop materialized view if exists derived.resolved_stations_view")

    with open(views_sql_dir / "archives" / "derived_resolved_stations_view_v1.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "derived_station_commodities_view_v3.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "archives" / "derived_hotspot_ring_view_v3.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "archives" / "derived_acquisition_routes_v2.sql") as f:
        op.execute(f.read())

    # Drop new indexes
    op.drop_index("ix_core_systems_cp_p_state_date", "systems", schema="core", if_exists=True)
    op.drop_index("ix_core_systems_powers", "systems", schema="core", if_exists=True)
    op.drop_index("ix_core_systems_p_state_date", "systems", schema="core", if_exists=True)
    op.drop_index(
        "ix_core_market_commodities_nonzero_supplydemand_updated_at",
        "market_commodities",
        schema="core",
        if_exists=True,
    )
