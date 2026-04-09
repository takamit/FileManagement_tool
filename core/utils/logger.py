from __future__ import annotations

import logging
from pathlib import Path

from config.logging_config import LOG_FILE_NAME, LOG_FORMAT, LOG_LEVEL


def configure_logger(project_root: Path, logger_name: str = "file_management_tool") -> logging.Logger:
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger

    log_dir = project_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / LOG_FILE_NAME, encoding="utf-8")
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger
