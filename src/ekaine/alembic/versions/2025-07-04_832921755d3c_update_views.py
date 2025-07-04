"""Update views

- `derived.mining_map_acquisition_routes_view` and `derived.hotspot_acquisition_routes_view`
    both now return the station controlling faction id

Revision ID: 832921755d3c
Revises: e5a84707f2a0
Create Date: 2025-07-04 01:00:34.837333

"""

from typing import Sequence

from alembic import op

from ekaine.common.constants import SQL_DIR

views_sql_dir = SQL_DIR / "views"


# revision identifiers, used by Alembic.
revision: str = "832921755d3c"
down_revision: str | None = "e5a84707f2a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("drop materialized view if exists derived.mining_map_acquisition_routes_view")
    op.execute("drop materialized view if exists derived.hotspot_acquisition_routes_view")

    with open(views_sql_dir / "m_derived_mining_map_acquisition_routes_view_v2.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "m_derived_hotspot_acquisition_routes_view_v2.sql") as f:
        op.execute(f.read())


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("drop materialized view if exists derived.mining_map_acquisition_routes_view")
    op.execute("drop materialized view if exists derived.hotspot_acquisition_routes_view")

    with open(views_sql_dir / "archives" / "m_derived_mining_map_acquisition_routes_view_v1.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "archives" / "m_derived_hotspot_acquisition_routes_view_v1.sql") as f:
        op.execute(f.read())
