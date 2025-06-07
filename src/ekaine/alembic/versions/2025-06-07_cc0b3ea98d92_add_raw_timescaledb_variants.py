"""Add raw timescaledb variants for data quality

Revision ID: cc0b3ea98d92
Revises: d235c814f80c
Create Date: 2025-06-07 12:02:16.855801

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from ekaine.common.constants import SQL_DIR

functions_sql_dir = SQL_DIR / "functions"

# revision identifiers, used by Alembic.
revision: str = "cc0b3ea98d92"
down_revision: str | None = "d235c814f80c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with open(functions_sql_dir / "derived_calculate_epoch_duration_since_timestamp_v1.sql") as f:
        op.execute(f.read())

    op.execute("CREATE SCHEMA IF NOT EXISTS raw_timescaledb")
    op.create_table(
        "faction_presences",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("system_id", sa.Integer(), nullable=False),
        sa.Column("faction_id", sa.Integer(), nullable=False),
        sa.Column("influence", sa.Float(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("happiness", sa.Text(), nullable=True),
        sa.Column("active_states", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("pending_states", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("recovering_states", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("is_backfilled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", "timestamp"),
        schema="raw_timescaledb",
    )
    op.create_table(
        "signals",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("system_id", sa.Integer(), nullable=False),
        sa.Column("signal_type", sa.TEXT(), nullable=True),
        sa.Column("signal_name", sa.TEXT(), nullable=True),
        sa.Column("is_station", sa.Boolean(), nullable=True),
        sa.Column("uss_type", sa.TEXT(), nullable=True),
        sa.Column("spawning_state", sa.TEXT(), nullable=True),
        sa.Column("spawning_faction", sa.TEXT(), nullable=True),
        sa.Column("spawning_power", sa.TEXT(), nullable=True),
        sa.Column("opposing_power", sa.TEXT(), nullable=True),
        sa.Column("threat_level", sa.SmallInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", "timestamp"),
        schema="raw_timescaledb",
    )
    op.create_table(
        "systems",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("system_id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("allegiance", sa.Text(), nullable=True),
        sa.Column("population", sa.BigInteger(), nullable=True),
        sa.Column("primary_economy", sa.Text(), nullable=True),
        sa.Column("secondary_economy", sa.Text(), nullable=True),
        sa.Column("security", sa.Text(), nullable=True),
        sa.Column("government", sa.Text(), nullable=True),
        sa.Column("controlling_faction_id", sa.Integer(), nullable=True),
        sa.Column("controlling_power", sa.Text(), nullable=True),
        sa.Column("power_conflict_progress", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("power_state", sa.Text(), nullable=True),
        sa.Column("power_state_control_progress", sa.Float(), nullable=True),
        sa.Column("power_state_reinforcement", sa.Float(), nullable=True),
        sa.Column("power_state_undermining", sa.Float(), nullable=True),
        sa.Column("powers", sa.ARRAY(sa.Text()), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("is_backfilled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", "timestamp"),
        schema="raw_timescaledb",
    )
    op.create_table(
        "power_conflict_progress",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("system_id", sa.Integer(), nullable=False),
        sa.Column("power_name", sa.Text(), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_backfilled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", "timestamp"),
        schema="raw_timescaledb",
    )
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
        schema="raw_timescaledb",
    )
    op.execute(
        "SELECT create_hypertable('raw_timescaledb.faction_presences', by_range('timestamp'), if_not_exists => TRUE);"
    )
    op.execute("SELECT create_hypertable('raw_timescaledb.signals', by_range('timestamp'), if_not_exists => TRUE);")
    op.execute("SELECT create_hypertable('raw_timescaledb.systems', by_range('timestamp'), if_not_exists => TRUE);")
    op.execute(
        "SELECT create_hypertable("
        "'raw_timescaledb.power_conflict_progress', by_range('timestamp'), if_not_exists => TRUE);"
    )
    op.execute(
        "SELECT create_hypertable("
        "'raw_timescaledb.market_commodity_faction_state', by_range('timestamp'), if_not_exists => TRUE);"
    )

    # Definitely did not forget to hypertable this in the previous revision...
    op.execute(
        "SELECT create_hypertable("
        "'timescaledb.market_commodity_faction_state', by_range('timestamp'), if_not_exists => TRUE);"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP SCHEMA IF EXISTS raw_timescaledb CASCADE")
    op.execute("drop view if exists derived.calculate_epoch_duration_since_timestamp")
