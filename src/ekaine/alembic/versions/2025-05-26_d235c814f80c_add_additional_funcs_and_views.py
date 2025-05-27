"""Create initial functions and views

Revision ID: d235c814f80c
Revises: 2920a950c2dc
Create Date: 2025-05-26 15:34:33.127403

"""

from typing import Sequence

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
    with open(views_sql_dir / "derived_acquisition_routes_v1.sql") as f:
        op.execute(f.read())


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("drop view if exists derived.acquisition_routes")
