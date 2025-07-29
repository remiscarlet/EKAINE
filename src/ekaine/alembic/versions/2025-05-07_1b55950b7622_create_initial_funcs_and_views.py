"""Create initial functions and views

Revision ID: 1b55950b7622
Revises: 6b82a9368504
Create Date: 2025-05-07 00:14:47.127403

"""

from typing import Sequence

from alembic import op

from ekaine.common.constants import SQL_DIR

functions_sql_dir = SQL_DIR / "functions"
views_sql_dir = SQL_DIR / "views"


# revision identifiers, used by Alembic.
revision: str = "1b55950b7622"
down_revision: str | None = "6b82a9368504"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with open(views_sql_dir / "archives" / "derived_resolved_stations_view_v1.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "archives" / "derived_station_commodities_view_v1.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "archives" / "derived_hotspot_ring_view_v1.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "derived_unoccupied_systems_view_v1.sql") as f:
        op.execute(f.read())
    with open(functions_sql_dir / "archives" / "derived_calculate_commodity_score_v1.sql") as f:
        op.execute(f.read())
    with open(functions_sql_dir / "archives" / "derived_get_top_buy_commodities_in_system_v1.sql") as f:
        op.execute(f.read())
    with open(functions_sql_dir / "archives" / "derived_get_top_sell_commodities_in_system_v1.sql") as f:
        op.execute(f.read())
    with open(functions_sql_dir / "derived_get_systems_with_power_and_state_v1.sql") as f:
        op.execute(f.read())
    with open(functions_sql_dir / "derived_get_systems_with_power_v1.sql") as f:
        op.execute(f.read())
    with open(functions_sql_dir / "derived_get_acquirable_systems_from_origin_v1.sql") as f:
        op.execute(f.read())
    with open(functions_sql_dir / "derived_get_expandable_systems_in_range_v1.sql") as f:
        op.execute(f.read())
    with open(functions_sql_dir / "api_get_acquirable_systems_from_origin_v1.sql") as f:
        op.execute(f.read())
    with open(functions_sql_dir / "api_get_expandable_systems_in_range_v1.sql") as f:
        op.execute(f.read())
    with open(functions_sql_dir / "archives" / "api_get_hotspots_in_system_by_commodities_v1.sql") as f:
        op.execute(f.read())
    with open(functions_sql_dir / "archives" / "api_get_hotspots_in_system_v1.sql") as f:
        op.execute(f.read())
    with open(functions_sql_dir / "api_get_systems_with_power_v1.sql") as f:
        op.execute(f.read())
    with open(functions_sql_dir / "archives" / "api_get_top_commodities_in_system_v1.sql") as f:
        op.execute(f.read())
    with open(functions_sql_dir / "archives" / "api_get_mining_expandable_systems_in_range_v1.sql") as f:
        op.execute(f.read())
    with open(functions_sql_dir / "archives" / "api_get_top_reinforcement_mining_routes_v1.sql") as f:
        op.execute(f.read())


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("drop function if exists api.get_top_reinforcement_mining_routes")
    op.execute("drop function if exists api.get_mining_expandable_systems_in_range")
    op.execute("drop function if exists api.get_acquirable_systems_from_origin")
    op.execute("drop function if exists api.get_expandable_systems_in_range")
    op.execute("drop function if exists api.get_hotspots_in_system")
    op.execute("drop function if exists api.get_hotspots_in_system_by_commodities")
    op.execute("drop function if exists api.get_top_commodities_in_system")
    op.execute("drop function if exists api.get_systems_with_power")
    op.execute("drop function if exists api.get_expandable_systems_in_range")
    op.execute("drop function if exists derived.get_systems_with_power_and_state")
    op.execute("drop function if exists derived.get_systems_with_power")
    op.execute("drop function if exists derived.get_acquirable_systems_from_origin")
    op.execute("drop function if exists derived.get_expandable_systems_in_range")
    op.execute("drop function if exists derived.get_top_buy_commodities_in_system")
    op.execute("drop function if exists derived.get_top_sell_commodities_in_system")
    op.execute("drop function if exists derived.calculate_commodity_score")
    op.execute("drop view if exists derived.hotspot_ring_view")
    op.execute("drop view if exists derived.station_commodities_view")
    op.execute("drop view if exists derived.resolved_stations_view")
    op.execute("drop view if exists derived.derived_unoccupied_systems_view")
