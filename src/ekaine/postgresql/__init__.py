import os
from typing import Any, Tuple

from sqlalchemy import Integer, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    scoped_session,
    sessionmaker,
)


class BaseModel(DeclarativeBase):
    unique_columns: Tuple[str, ...] = ()
    __abstract__ = True

    def to_cache_key(self, *args: Any, **kwargs: Any) -> int:
        return hash(self.to_cache_key_tuple(*args, **kwargs))

    def to_cache_key_tuple(self, *args: Any, **kwargs: Any) -> Tuple[Any, ...]:
        raise NotImplementedError("Declarative BaseModel's to_cache_key_tuple() unimplemented")


class BaseModelWithId(BaseModel):
    __abstract__ = True
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ekaine:ekaine_pw@localhost:5432/ekaine")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,  # Set to True for SQL query debug logs
)

SessionLocal = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))
