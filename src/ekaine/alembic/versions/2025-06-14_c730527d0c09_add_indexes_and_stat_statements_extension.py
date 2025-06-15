"""Add indexes and stat statements

Revision ID: c730527d0c09
Revises: eafd00ec8a72
Create Date: 2025-06-14 20:31:27.474928

"""

from typing import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c730527d0c09"
down_revision: str | None = "eafd00ec8a72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("create extension pg_stat_statements")

    # core.commodities
    op.create_index(op.f("ix_core_commodities_name"), "commodities", ["name"], unique=True, schema="core")
    op.create_index(op.f("ix_core_commodities_rare_goods"), "commodities", ["rare_goods"], unique=False, schema="core")
    op.create_index(op.f("ix_core_commodities_corrosive"), "commodities", ["corrosive"], unique=False, schema="core")
    op.create_index(op.f("ix_core_commodities_category"), "commodities", ["category"], unique=False, schema="core")
    op.create_index(
        op.f("ix_core_commodities_is_mineable"), "commodities", ["is_mineable"], unique=False, schema="core"
    )
    op.create_index(op.f("ix_core_commodities_ring_types"), "commodities", ["ring_types"], unique=False, schema="core")
    op.create_index(
        op.f("ix_core_commodities_mining_method"), "commodities", ["mining_method"], unique=False, schema="core"
    )
    op.create_index(
        op.f("ix_core_commodities_has_hotspots"), "commodities", ["has_hotspots"], unique=False, schema="core"
    )

    # core.bodies
    op.create_index(op.f("ix_core_bodies_name"), "bodies", ["name"], unique=False, schema="core")

    # core.faction_presences
    op.create_index(
        op.f("ix_core_faction_presences_updated_at"), "faction_presences", ["updated_at"], unique=False, schema="core"
    )
    op.create_index(
        op.f("ix_core_faction_presences_state"), "faction_presences", ["state"], unique=False, schema="core"
    )
    op.create_index(
        op.f("ix_core_faction_presences_active_state"),
        "faction_presences",
        ["active_states"],
        unique=False,
        schema="core",
    )

    # core.hotspots
    op.create_index(op.f("ix_core_hotspots_commodity_sym"), "hotspots", ["commodity_sym"], unique=False, schema="core")

    # core.market_commodities
    op.create_index(
        op.f("ix_core_market_commodities_commodity_sym"),
        "market_commodities",
        ["commodity_sym"],
        unique=False,
        schema="core",
    )
    op.create_index(
        op.f("ix_core_market_commodities_updated_at"), "market_commodities", ["updated_at"], unique=False, schema="core"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # core.market_commodities
    op.drop_index("ix_core_market_commodities_commodity_sym", "market_commodities", schema="core")
    op.drop_index("ix_core_market_commodities_updated_at", "market_commodities", schema="core")

    # core.hotspots
    op.drop_index("ix_core_hotspots_commodity_sym", "hotspots", schema="core")

    # core.faction_presences
    op.drop_index("ix_core_faction_presences_updated_at", "faction_presences", schema="core")
    op.drop_index("ix_core_faction_presences_state", "faction_presences", schema="core")
    op.drop_index("ix_core_faction_presences_active_state", "faction_presences", schema="core")

    # core.bodies
    op.drop_index("ix_core_bodies_name", "bodies", schema="core")

    # core.commodities
    op.drop_index("ix_core_commodities_name", "commodities", schema="core")
    op.drop_index("ix_core_commodities_rare_goods", "commodities", schema="core")
    op.drop_index("ix_core_commodities_corrosive", "commodities", schema="core")
    op.drop_index("ix_core_commodities_category", "commodities", schema="core")
    op.drop_index("ix_core_commodities_is_mineable", "commodities", schema="core")
    op.drop_index("ix_core_commodities_ring_types", "commodities", schema="core")
    op.drop_index("ix_core_commodities_mining_method", "commodities", schema="core")
    op.drop_index("ix_core_commodities_has_hotspots", "commodities", schema="core")

    op.execute("drop extension if exists pg_stat_statements")
