import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path

from app.core.paths import LOG_DIR

DEFAULT_LOG_DIR = LOG_DIR
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _managed_handler(handler: logging.Handler) -> logging.Handler:
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    setattr(handler, "_enterprise_ai_handler", True)
    return handler


def configure_logging(log_dir: str | Path | None = None) -> Path:
    """Configure idempotent application file and console logging."""
    target_dir = Path(log_dir) if log_dir is not None else Path(os.getenv("APP_LOG_DIR", DEFAULT_LOG_DIR))
    target_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    for handler in list(root_logger.handlers):
        if getattr(handler, "_enterprise_ai_handler", False):
            root_logger.removeHandler(handler)
            handler.close()

    app_handler = _managed_handler(RotatingFileHandler(
        target_dir / "app.log", maxBytes=10 * 1024 * 1024,
        backupCount=5, encoding="utf-8",
    ))
    app_handler.setLevel(logging.INFO)

    error_handler = _managed_handler(RotatingFileHandler(
        target_dir / "error.log", maxBytes=10 * 1024 * 1024,
        backupCount=5, encoding="utf-8",
    ))
    error_handler.setLevel(logging.ERROR)

    console_handler = _managed_handler(logging.StreamHandler())
    console_handler.setLevel(logging.INFO)

    root_logger.addHandler(app_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)
    logging.getLogger(__name__).info("Logging configured log_dir=%s", target_dir)
    return target_dir
