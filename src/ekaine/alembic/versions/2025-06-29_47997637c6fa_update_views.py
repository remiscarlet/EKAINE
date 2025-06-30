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


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("drop materialized view if exists derived.hotspot_acquisition_routes_view")
    op.execute("drop materialized view if exists derived.mining_map_acquisition_routes_view")
    op.execute("drop view if exists derived.potential_acquisition_routes_view")

    with open(views_sql_dir / "archives" / "derived_acquisition_routes_v4.sql") as f:
        op.execute(f.read())
