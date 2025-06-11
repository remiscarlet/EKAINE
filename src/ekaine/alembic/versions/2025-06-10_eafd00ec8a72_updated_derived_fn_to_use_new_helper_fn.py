"""Update derived funcs to use new helper funcs

Revision ID: eafd00ec8a72
Revises: 40976b15c3d7
Create Date: 2025-06-10 18:08:25.245152

"""

from typing import Sequence

from alembic import op

from ekaine.common.constants import SQL_DIR

functions_sql_dir = SQL_DIR / "functions"

# revision identifiers, used by Alembic.
revision: str = "eafd00ec8a72"
down_revision: str | None = "40976b15c3d7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("drop function if exists derived.get_top_buy_commodities_in_system")
    with open(functions_sql_dir / "derived_get_top_buy_commodities_in_system_v2.sql") as f:
        op.execute(f.read())

    op.execute("drop function if exists derived.get_top_sell_commodities_in_system")
    with open(functions_sql_dir / "derived_get_top_sell_commodities_in_system_v2.sql") as f:
        op.execute(f.read())


def downgrade() -> None:
    """Downgrade schema.

    This one's kinda fucked.
    I messed up and moved a helper func between schemas, but didn't update the dependent functions using the helper
    This means this downgrade function technically needs to downgrade into an invalid state
    where calling the `get_top_X_commodities` _will_ fail because of the missing helper func.

    """

    # Temporarily load the old helper
    with open(functions_sql_dir / "archives" / "derived_calculate_commodity_score_v1.sql") as f:
        op.execute(f.read())
    # Drop new versions
    op.execute("drop function if exists derived.get_top_buy_commodities_in_system")
    op.execute("drop function if exists derived.get_top_sell_commodities_in_system")
    # Load old versions
    with open(functions_sql_dir / "archives" / "derived_get_top_buy_commodities_in_system_v1.sql") as f:
        op.execute(f.read())
    with open(functions_sql_dir / "archives" / "derived_get_top_sell_commodities_in_system_v1.sql") as f:
        op.execute(f.read())
    # Drop old helper, which will make the old top commodity func no longer work.
    op.execute("drop function if exists derived.calculate_commodity_score_v1")
