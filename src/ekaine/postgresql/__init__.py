from typing import Any, Tuple

from sqlalchemy import Integer, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    scoped_session,
    sessionmaker,
)

from ekaine.common.constants import EKAINE_DATABASE_URL, GRAFANA_DATABASE_URL


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


engine = create_engine(
    EKAINE_DATABASE_URL,
    connect_args={"ssl": None},
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,  # Set to True for SQL query debug logs
)
SessionLocalEkaine = scoped_session(sessionmaker(bind=engine, autocommit=False, autoflush=False))


async_engine = create_async_engine(
    GRAFANA_DATABASE_URL.replace("postgresql:", "postgresql+asyncpg:"),
    connect_args={"ssl": None},
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,  # Set to True for SQL query debug logs
)
AsyncSessionLocalGrafana: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    autoflush=False,
)
