"""Update views

Revision ID: be5cda8acaec
Revises: c730527d0c09
Create Date: 2025-06-15 00:27:08.956709

Updates:
- derived.station_commodities_view v1 -> v2
- derived.acquisition_routes v1 -> v2
"""

from typing import Sequence

from alembic import op

from ekaine.common.constants import SQL_DIR

views_sql_dir = SQL_DIR / "views"

# revision identifiers, used by Alembic.
revision: str = "be5cda8acaec"
down_revision: str | None = "c730527d0c09"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("drop view if exists derived.acquisition_routes")
    op.execute("drop view if exists derived.station_commodities_view")

    with open(views_sql_dir / "archives" / "derived_station_commodities_view_v2.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "derived_acquisition_routes_v2.sql") as f:
        op.execute(f.read())


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("drop view if exists derived.acquisition_routes")
    op.execute("drop view if exists derived.station_commodities_view")

    with open(views_sql_dir / "archives" / "derived_station_commodities_view_v1.sql") as f:
        op.execute(f.read())
    with open(views_sql_dir / "archives" / "derived_acquisition_routes_v1.sql") as f:
        op.execute(f.read())
