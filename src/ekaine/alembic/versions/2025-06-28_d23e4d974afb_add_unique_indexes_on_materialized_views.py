"""Update materialized views

Revision ID: d23e4d974afb
Revises: 2ded584f2cc5
Create Date: 2025-06-28 11:33:40.721650

"""

from typing import Sequence

from alembic import op

from ekaine.common.constants import SQL_DIR

views_sql_dir = SQL_DIR / "views"


# revision identifiers, used by Alembic.
revision: str = "d23e4d974afb"
down_revision: str | None = "2ded584f2cc5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("drop materialized view if exists derived.acquisition_routes")
    op.execute("drop materialized view if exists derived.hotspot_ring_view")
    op.execute("drop view if exists derived.station_commodities_view")
    op.execute("drop materialized view if exists derived.resolved_stations_view")
    op.execute("drop materialized view if exists derived.average_ring_metadata_view")

    with open(views_sql_dir / "m_derived_average_ring_metadata_view_v2.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "m_derived_resolved_stations_view_v3.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "derived_station_commodities_view_v3.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "archives" / "m_derived_hotspot_ring_view_v5.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "archives" / "derived_acquisition_routes_v4.sql") as f:
        op.execute(f.read())


def downgrade() -> None:
    """Downgrade schema."""
    # Update views
    op.execute("drop materialized view if exists derived.acquisition_routes")
    op.execute("drop materialized view if exists derived.hotspot_ring_view")
    op.execute("drop view if exists derived.station_commodities_view")
    op.execute("drop materialized view if exists derived.resolved_stations_view")

    with open(views_sql_dir / "archives" / "derived_resolved_stations_view_v2.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "derived_station_commodities_view_v3.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "archives" / "derived_hotspot_ring_view_v4.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "archives" / "derived_acquisition_routes_v3.sql") as f:
        op.execute(f.read())

    with open(views_sql_dir / "archives" / "derived_average_ring_metadata_view_v1.sql") as f:
        op.execute(f.read())
