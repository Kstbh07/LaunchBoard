
import logging
import sys
from typing import Optional

import structlog
from structlog.types import Processor

from app.core.config import get_settings


def bind_request_id(request_id: str) -> None:
    structlog.contextvars.bind_contextvars(request_id=request_id)


def clear_request_id() -> None:
    structlog.contextvars.unbind_contextvars("request_id")


def setup_logging() -> None:
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    is_production = settings.ENVIRONMENT.lower() in ("production", "prod")

    # Shared processors: safe for both structlog and standard logging.
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    renderer: Processor = (
        structlog.processors.JSONRenderer()
        if is_production
        else structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())
    )

    # filter_by_level belongs only to structlog.
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    for lib in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        lib_logger = logging.getLogger(lib)
        lib_logger.handlers.clear()
        lib_logger.propagate = True


setup_logging()


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
