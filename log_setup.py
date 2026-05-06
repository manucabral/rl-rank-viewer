"""Logging."""

import logging
import sys

_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
_DATE_FORMAT = "%H:%M:%S"


def setup_logger(level: int = logging.DEBUG) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT, _DATE_FORMAT))
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)
    _suppress_noisy_loggers()


def _suppress_noisy_loggers() -> None:
    class _FilterMalformedConfig(logging.Filter):
        def filter(self, record):
            return "skipped malformed config line" not in record.getMessage()

    logging.getLogger("rlstatsapi.config").addFilter(_FilterMalformedConfig())
    logging.getLogger("rlstatsapi").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
