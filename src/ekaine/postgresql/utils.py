import re
import traceback
from typing import Any, Type

from sqlalchemy.dialects.postgresql import Insert as PGInsert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql.dml import ReturningInsert

from ekaine.common.logging import get_logger
from ekaine.postgresql import BaseModel

logger = get_logger(__name__)


def upsert_all[T: BaseModel](
    session: Session,
    model: Type[T],
    rows: list[dict[str, Any]],
    exclude_update_cols: list[str] | None = None,
    debug_print_extra_cols: list[str] | None = None,
) -> list[T]:
    """Upserts a list of dicts representing sqlalchemy objects"""
    if not rows:
        return []
    debug_print_extra_cols = debug_print_extra_cols or []
    exclude_update_cols = exclude_update_cols or []
    exclude_update_cols.append("id")  # Never update id column

    conflict_cols = list(model.unique_columns or [])
    cols_to_print = conflict_cols + debug_print_extra_cols
    logger.debug(f"{len(rows)} {model.__name__} items being upserted...")
    logger.trace(repr([{k: v for k, v in item.items() if k in cols_to_print} for item in rows]))

    updatable_cols = [
        col for col in model.__table__.columns if col.name not in conflict_cols and col.name not in exclude_update_cols
    ]

    insert_stmt: PGInsert = pg_insert(model).values(rows)
    excluded = insert_stmt.excluded  # This line actually matters. Must explicitly grab 'excluded' namespace
    coalesce_updates = {
        col: (getattr(excluded, col.name) if hasattr(excluded, col.name) else model.__table__.c[col.name])
        for col in updatable_cols
    }

    returning_stmt: ReturningInsert[tuple[T]] = insert_stmt.on_conflict_do_update(
        index_elements=conflict_cols,
        set_=coalesce_updates,
    ).returning(model)

    try:
        results = session.scalars(returning_stmt, execution_options={"populate_existing": True})
        session.commit()
        return list(iter(results.all()))
    except SQLAlchemyError:
        session.rollback()
        logger.error(f"Transaction failed: {traceback.format_exc()}")

    return []


dollar_string_to_db_val_re = re.compile(r"\$\w+_(?P<val>.*)")


def dollar_string_to_db_val(s: str) -> str:
    result = dollar_string_to_db_val_re.match(s)
    if result is None:
        logger.warning(f"Could not convert dollar string to db val - got malformed dollar string! '{s}'")
        raise ValueError(f"Malformed dollar string '{s}'")
    val = result.group("val")
    val_capitalized = " ".join(list(map(lambda v: v.capitalize(), val.split("_"))))
    return val_capitalized
