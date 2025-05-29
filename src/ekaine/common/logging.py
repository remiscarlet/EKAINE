import logging
import logging.config
from argparse import Namespace
from typing import cast

from ekaine.common.constants import DEFAULT_LOG_LEVEL, LOG_DIR
from ekaine.common.logging_bootstrap import TRACE_LEVEL_NUM, TraceLogger

LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "minimal": {
            # "format": "[%(levelname)s][%(name)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "standard": {
            "format": "[%(asctime)s][%(levelname)s][%(name)s]: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "minimal",
            "level": "TRACE",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "TRACE",
            "formatter": "standard",
            "filename": str(LOG_DIR / "app.log"),
            "mode": "a",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "encoding": "utf-8",
        },
        "warning-file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "WARNING",
            "formatter": "standard",
            "filename": str(LOG_DIR / "app-warnings.log"),
            "mode": "a",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "encoding": "utf-8",
        },
    },
    "root": {
        "level": DEFAULT_LOG_LEVEL,
        "handlers": ["console", "file", "warning-file"],
    },
}

# class TraceableLogger(Protocol):
#     def trace(self, msg: str, *args: Any, **kws: Any) -> None: ...
#     def debug(self, msg: str, *args: Any, **kws: Any) -> None: ...
#     def info(self, msg: str, *args: Any, **kws: Any) -> None: ...
#     def warning(self, msg: str, *args: Any, **kws: Any) -> None: ...
#     def error(self, msg: str, *args: Any, **kws: Any) -> None: ...


def get_logger(name: str) -> TraceLogger:
    return cast(TraceLogger, logging.getLogger(name))


def configure_logger_cli(args: Namespace) -> None:
    match args.verbosity:
        case 0:
            level = logging.getLevelNamesMapping().get(DEFAULT_LOG_LEVEL, logging.INFO)
        case 1:
            level = logging.DEBUG
        case _:
            level = TRACE_LEVEL_NUM
    configure_logger(level)


def configure_logger(level: int) -> None:
    logging.config.dictConfig(LOGGING_CONFIG)

    root = logging.getLogger()
    root.setLevel(level)

    for name, logger in logging.root.manager.loggerDict.items():
        if not isinstance(logger, logging.Logger):
            continue
        logger.setLevel(level)

    for name in [
        "sqlalchemy",
        "sqlalchemy.dialects",
        "sqlalchemy.dialects.postgresql",
        "sqlalchemy.engine",
        "sqlalchemy.engine.Connection",
        "sqlalchemy.engine.Engine",
        "sqlalchemy.engine.base.Engine",
        "sqlalchemy.orm.dependency",
        "sqlalchemy.orm.instrumentation",
        "sqlalchemy.orm.mapper",
        "sqlalchemy.orm.mapper.Mapper",
        "sqlalchemy.orm.path_registry",
        "sqlalchemy.orm.properties",
        "sqlalchemy.orm.relationships",
        "sqlalchemy.orm.relationships.RelationshipProperty",
        "sqlalchemy.orm.strategies.LazyLoader",
        "sqlalchemy.pool",
        "sqlalchemy.pool.impl.QueuePool",
    ]:
        logging.getLogger(name).setLevel(logging.WARNING)

    logging.getLogger("sqlalchemy.engine").disabled = True
