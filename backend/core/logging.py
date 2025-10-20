from __future__ import annotations

import logging
import logging.config
from typing import Any, Dict

import structlog

from .settings import settings


def get_logging_config() -> Dict[str, Any]:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structlog": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.processors.JSONRenderer(),
                "foreign_pre_chain": [
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.add_logger_name,
                    structlog.processors.TimeStamper(fmt="iso"),
                ],
            }
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "structlog",
            }
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["default"],
        },
    }


def configure_logging() -> None:
    logging.config.dictConfig(get_logging_config())
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()
