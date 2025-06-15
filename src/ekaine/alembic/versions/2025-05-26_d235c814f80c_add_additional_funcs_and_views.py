"""Add additional functions and views

Revision ID: d235c814f80c
Revises: 2920a950c2dc
Create Date: 2025-05-26 15:34:33.127403

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

from ekaine.common.constants import SQL_DIR

functions_sql_dir = SQL_DIR / "functions"
views_sql_dir = SQL_DIR / "views"


# revision identifiers, used by Alembic.
revision: str = "d235c814f80c"
down_revision: str | None = "2920a950c2dc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("market_commodities", sa.Column("demand_bracket", sa.SmallInteger(), nullable=True), schema="core")
    op.add_column("market_commodities", sa.Column("supply_bracket", sa.SmallInteger(), nullable=True), schema="core")

    with open(views_sql_dir / "archives" / "derived_acquisition_routes_v1.sql") as f:
        op.execute(f.read())

    op.create_table(
        "market_commodity_faction_state",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("system_id", sa.Integer(), nullable=False, index=True),
        sa.Column("sy_cf_id", sa.Integer(), nullable=False, index=True),
        sa.Column("sy_cf_state", sa.Text(), nullable=False, index=True),
        sa.Column("sy_cf_active_states", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("station_id", sa.Integer(), nullable=False, index=True),
        sa.Column("st_cf_id", sa.Integer(), nullable=False, index=True),
        sa.Column("st_cf_state", sa.Text(), nullable=False, index=True),
        sa.Column("st_cf_active_states", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("commodity_sym", sa.Text(), nullable=False, index=True),
        sa.Column("sell_price_multiplier", sa.Float(), nullable=False),
        sa.Column("buy_price_multiplier", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id", "timestamp"),
        schema="timescaledb",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("market_commodity_faction_state", schema="timescaledb")
    op.execute("drop view if exists derived.acquisition_routes")
    op.drop_column("market_commodities", "supply_bracket", schema="core")
    op.drop_column("market_commodities", "demand_bracket", schema="core")
