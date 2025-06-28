"""Add ring geometry, computed cols

Revision ID: 0b35f9d0307b
Revises: df38aedf45b0
Create Date: 2025-06-26 21:24:32.636347

"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = "0b35f9d0307b"
down_revision: str | None = "df38aedf45b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index("idx_systems_coords", table_name="systems", schema="core", if_exists=True)
    op.create_index(
        "ix_systems_coords_3d",
        "systems",
        ["coords"],
        unique=False,
        postgresql_using="gist",
        postgresql_ops={"coords": "gist_geometry_ops_nd"},
        schema="core",
    )
    # 1) ring_geom: a STORED generated column
    op.add_column(
        "rings",
        sa.Column(
            "ring_geom",
            Geometry("POLYGON", srid=0),
            sa.Computed(
                """
                ST_Difference(
                  ST_Buffer( ST_MakePoint(0,0), outer_radius ),
                  ST_Buffer( ST_MakePoint(0,0), inner_radius )
                )
                """,
                persisted=True,
            ),
            nullable=True,
        ),
        schema="core",
    )

    # 2) ring_area: area of the ring_geom
    op.add_column(
        "rings",
        sa.Column(
            "ring_area",
            sa.Float(),
            sa.Computed(
                """
                ST_Area(ST_Difference(
                  ST_Buffer( ST_MakePoint(0,0), outer_radius ),
                  ST_Buffer( ST_MakePoint(0,0), inner_radius )
                ))""",
                persisted=True,
            ),
            nullable=True,
        ),
        schema="core",
    )

    # 3) surface_density: mass per unit area
    op.add_column(
        "rings",
        sa.Column(
            "surface_density",
            sa.Float(),
            sa.Computed(
                """
                mass / NULLIF(ST_Area(ST_Difference(
                  ST_Buffer( ST_MakePoint(0,0), outer_radius ),
                  ST_Buffer( ST_MakePoint(0,0), inner_radius )
                )),0)""",
                persisted=True,
            ),
            nullable=True,
        ),
        schema="core",
    )

    # 4) GiST index on ring_geom for any spatial lookups
    op.create_index(
        "ix_core_rings_ring_geom",
        "rings",
        ["ring_geom"],
        unique=False,
        postgresql_using="gist",
        schema="core",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_rings_ring_geom", table_name="rings", schema="core")
    op.drop_column("rings", "surface_density", schema="core")
    op.drop_column("rings", "ring_area", schema="core")
    op.drop_column("rings", "ring_geom", schema="core")

    op.drop_index("ix_systems_coords_3d", table_name="systems", schema="core", if_exists=True)
    op.create_index(
        "idx_systems_coords",
        "systems",
        ["coords"],
        unique=False,
        postgresql_using="gist",
        schema="core",
    )
