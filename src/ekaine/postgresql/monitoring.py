from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Integer,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ekaine.postgresql import BaseModel


class HypertableSizeTimeseries(BaseModel):
    __tablename__ = "hypertable_sizes"
    __table_args__ = (
        PrimaryKeyConstraint("id", "timestamp"),
        UniqueConstraint("schema_name", "table_name", "timestamp", name="_monitoring_ht_sizes_schm_tbl_n_ts_uc"),
        {"schema": "monitoring"},
    )

    id: Mapped[int] = mapped_column(Integer, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)

    schema_name: Mapped[str] = mapped_column(String)
    table_name: Mapped[str] = mapped_column(String)

    size: Mapped[Optional[int]] = mapped_column(Integer)
    row_estimate: Mapped[Optional[int]] = mapped_column(Integer)
