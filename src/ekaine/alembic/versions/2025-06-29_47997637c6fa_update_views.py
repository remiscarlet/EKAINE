"""Update views

- Acquisition Routes
  - Remove hardcoded date filter

Revision ID: 47997637c6fa
Revises: dfa9d94d00e0
Create Date: 2025-06-29 12:48:44.092925

"""

from typing import Sequence

from alembic import op

from ekaine.common.constants import SQL_DIR

views_sql_dir = SQL_DIR / "views"


# revision identifiers, used by Alembic.
revision: str = "47997637c6fa"
down_revision: str | None = "dfa9d94d00e0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("drop materialized view if exists derived.acquisition_routes")

    with open(views_sql_dir / "derived_potential_acquisition_routes_view_v1.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "m_derived_hotspot_acquisition_routes_view_v1.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "m_derived_mining_map_acquisition_routes_view_v1.sql") as f:
        op.execute(f.read())

    op.execute("SELECT cron.unschedule('refresh_derived_average_ring_metadata_view')")
    op.execute("SELECT cron.unschedule('refresh_derived_resolved_stations_view')")
    op.execute("SELECT cron.unschedule('refresh_derived_hotspot_ring_view')")
    op.execute("SELECT cron.unschedule('refresh_derived_acquisition_routes')")

    every = 10  # minutes
    # "Layer 1"
    op.execute(
        "SELECT cron.schedule('refresh_derived_hotspot_ring_view', "
        f"'0-59/{every} * * * *', $$REFRESH MATERIALIZED VIEW CONCURRENTLY derived.hotspot_ring_view;$$);"
    )
    op.execute(
        "SELECT cron.schedule('refresh_derived_resolved_stations_view', "
        f"'1-59/{every} * * * *', $$REFRESH MATERIALIZED VIEW CONCURRENTLY derived.resolved_stations_view;$$);"
    )

    # "Layer 2"
    op.execute(
        "SELECT cron.schedule('refresh_derived_mining_map_acquisition_routes_view', "
        f"'5-59/{every} * * * *', "
        "$$REFRESH MATERIALIZED VIEW CONCURRENTLY derived.mining_map_acquisition_routes_view;$$);"
    )
    op.execute(
        "SELECT cron.schedule('refresh_derived_hotspot_acquisition_routes_view', "
        f"'6-59/{every} * * * *', "
        "$$REFRESH MATERIALIZED VIEW CONCURRENTLY derived.hotspot_acquisition_routes_view;$$);"
    )

    # Once a day at midnight
    op.execute(
        "SELECT cron.schedule('refresh_derived_average_ring_metadata_view', "
        "'8 0 * * *', $$REFRESH MATERIALIZED VIEW CONCURRENTLY derived.average_ring_metadata_view;$$);"
    )
    op.execute(
        "SELECT cron.schedule('refresh_derived_commodity_prices_view', "
        "'9 0 * * *', $$REFRESH MATERIALIZED VIEW CONCURRENTLY derived.commodity_prices_view;$$);"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("drop materialized view if exists derived.hotspot_acquisition_routes_view")
    op.execute("drop materialized view if exists derived.mining_map_acquisition_routes_view")
    op.execute("drop view if exists derived.potential_acquisition_routes_view")

    with open(views_sql_dir / "archives" / "derived_acquisition_routes_v4.sql") as f:
        op.execute(f.read())

    # Refresh crons
    op.execute("SELECT cron.unschedule('refresh_derived_hotspot_ring_view')")
    op.execute("SELECT cron.unschedule('refresh_derived_resolved_stations_view')")
    op.execute("SELECT cron.unschedule('refresh_derived_mining_map_acquisition_routes_view')")
    op.execute("SELECT cron.unschedule('refresh_derived_hotspot_acquisition_routes_view')")
    op.execute("SELECT cron.unschedule('refresh_derived_average_ring_metadata_view')")
    op.execute("SELECT cron.unschedule('refresh_derived_commodity_prices_view')")

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
