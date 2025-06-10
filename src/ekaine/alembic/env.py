import os
from logging.config import fileConfig
from typing import Literal

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.schema import SchemaItem

import ekaine.postgresql.db  # noqa: F401
import ekaine.postgresql.monitoring  # noqa: F401
import ekaine.postgresql.timeseries  # noqa: F401
from ekaine.postgresql import BaseModel

config = context.config
fileConfig(config.config_file_name or "")

target_metadata = BaseModel.metadata

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ekaine:ekaine_pw@localhost:5432/ekaine")
config.set_main_option("sqlalchemy.url", DATABASE_URL)

APP_SCHEMAS = {"core", "derived", "api", "raw_timescaledb", "timescaledb", "helpers", "monitoring"}


def include_object(
    object: SchemaItem,
    name: str | None,
    type_: Literal["schema", "table", "column", "index", "unique_constraint", "foreign_key_constraint"],
    reflected: bool,
    compare_to: SchemaItem | None,
) -> bool:
    return getattr(object, "schema", None) in APP_SCHEMAS


def run_migrations_offline() -> None:
    print("Running Offline Migration")
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        include_schemas=True,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    print("Running Online Migration")
    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            include_schemas=True,
            include_object=include_object,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


print(f"Using DB URL: {config.get_main_option('sqlalchemy.url')}")

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
