"""Create readonly ekaine user

Revision ID: 2086129b5566
Revises: be5cda8acaec
Create Date: 2025-06-16 20:01:20.585511

"""

from typing import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2086129b5566"
down_revision: str | None = "be5cda8acaec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


schemas = ["cron", "monitoring", "core", "derived", "helpers", "api", "timescaledb", "raw_timescaledb"]
readonly_user = "ekaine_readonly"


def upgrade() -> None:
    """Upgrade schema."""

    op.execute(f"CREATE USER {readonly_user} WITH PASSWORD 'ekaine_readonly_pw'")
    op.execute(f"GRANT CONNECT ON DATABASE ekaine TO {readonly_user}")

    for schema in schemas:
        op.execute(f"GRANT USAGE ON SCHEMA {schema} TO {readonly_user}")
        op.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA {schema} TO {readonly_user}")
        op.execute(f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {schema} TO {readonly_user}")
        op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT SELECT ON TABLES TO {readonly_user}")
        op.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} GRANT EXECUTE ON FUNCTIONS TO {readonly_user}")

    # pg_cron needs explicit grants
    op.execute(f"GRANT SELECT ON cron.job TO {readonly_user}")
    op.execute(f"GRANT SELECT ON cron.job_run_details TO {readonly_user}")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(f"REVOKE SELECT ON cron.job FROM {readonly_user}")
    op.execute(f"REVOKE SELECT ON cron.job_run_details FROM {readonly_user}")

    for schema in schemas:
        op.execute(f"REVOKE USAGE ON SCHEMA {schema} FROM {readonly_user}")
        op.execute(f"REVOKE SELECT ON ALL TABLES IN SCHEMA {schema} FROM {readonly_user}")
        op.execute(f"REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA {schema} FROM {readonly_user}")
        op.execute(
            f"ALTER DEFAULT PRIVILEGES FOR ROLE ekaine IN SCHEMA {schema} "
            f"REVOKE SELECT ON TABLES FROM {readonly_user}"
        )
        op.execute(
            f"ALTER DEFAULT PRIVILEGES FOR USER ekaine IN SCHEMA {schema} "
            f"REVOKE EXECUTE ON FUNCTIONS FROM {readonly_user}"
        )

    op.execute(f"REVOKE CONNECT ON DATABASE ekaine FROM {readonly_user}")
    op.execute(f"DROP ROLE IF EXISTS {readonly_user}")
