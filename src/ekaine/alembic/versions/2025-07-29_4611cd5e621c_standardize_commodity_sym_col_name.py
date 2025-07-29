"""Standardize commodity_sym column names

Revision ID: 4611cd5e621c
Revises: 832921755d3c
Create Date: 2025-07-29 11:00:53.779203

"""

from typing import Sequence

from alembic import op

from ekaine.common.constants import SQL_DIR

funcs_sql_dir = SQL_DIR / "functions"
views_sql_dir = SQL_DIR / "views"

# revision identifiers, used by Alembic.
revision: str = "4611cd5e621c"
down_revision: str | None = "832921755d3c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("drop function if exists api.get_hotspots_in_system_by_commodities")
    op.execute("drop function if exists api.get_hotspots_in_system")
    op.execute("drop function if exists api.get_mining_expandable_systems_in_range")
    op.execute("drop function if exists api.get_top_commodities_in_system")
    op.execute("drop function if exists api.get_top_reinforcement_mining_routes")

    op.execute("drop materialized view if exists derived.hotspot_acquisition_routes_view")
    op.execute("drop materialized view if exists derived.hotspot_ring_view")

    # Views
    with open(views_sql_dir / "m_derived_hotspot_ring_view_v6.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "m_derived_hotspot_acquisition_routes_view_v3.sql") as f:
        op.execute(f.read())

    # Funcs
    with open(funcs_sql_dir / "api_get_hotspots_in_system_by_commodities_v2.sql") as f:
        op.execute(f.read())
    with open(funcs_sql_dir / "api_get_hotspots_in_system_v2.sql") as f:
        op.execute(f.read())
    with open(funcs_sql_dir / "api_get_mining_expandable_systems_in_range_v2.sql") as f:
        op.execute(f.read())
    with open(funcs_sql_dir / "api_get_top_commodities_in_system_v2.sql") as f:
        op.execute(f.read())
    with open(funcs_sql_dir / "api_get_top_reinforcement_mining_routes_v2.sql") as f:
        op.execute(f.read())


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("drop function if exists api.get_hotspots_in_system_by_commodities")
    op.execute("drop function if exists api.get_hotspots_in_system")
    op.execute("drop function if exists api.get_mining_expandable_systems_in_range")
    op.execute("drop function if exists api.get_top_commodities_in_system")
    op.execute("drop function if exists api.get_top_reinforcement_mining_routes")

    op.execute("drop materialized view if exists derived.hotspot_acquisition_routes_view")
    op.execute("drop materialized view if exists derived.hotspot_ring_view")

    # Views
    with open(views_sql_dir / "archives" / "m_derived_hotspot_ring_view_v5.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "archives" / "m_derived_hotspot_acquisition_routes_view_v2.sql") as f:
        op.execute(f.read())

    # Functions
    with open(funcs_sql_dir / "archives" / "api_get_hotspots_in_system_by_commodities_v1.sql") as f:
        op.execute(f.read())
    with open(funcs_sql_dir / "archives" / "api_get_hotspots_in_system_v1.sql") as f:
        op.execute(f.read())
    with open(funcs_sql_dir / "archives" / "api_get_mining_expandable_systems_in_range_v1.sql") as f:
        op.execute(f.read())
    with open(funcs_sql_dir / "archives" / "api_get_top_commodities_in_system_v1.sql") as f:
        op.execute(f.read())
    with open(funcs_sql_dir / "archives" / "api_get_top_reinforcement_mining_routes_v1.sql") as f:
        op.execute(f.read())
