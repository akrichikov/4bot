from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logging(
    name: str,
    logs_dir: Path,
    level: int = logging.INFO,
    json_mode: bool = False,
    max_bytes: int = 512 * 1024,
    backup_count: int = 3,
) -> logging.Logger:
    """Configure and return a named logger with a rotating file handler.

    Idempotent: if a handler for the target file already exists on the logger,
    it won't add another one.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    logs_dir = Path(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)
    logfile = logs_dir / f"{name}.log"

    # Avoid duplicate handlers for the same file
    for h in logger.handlers:
        if isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == str(logfile):
            return logger

    handler = RotatingFileHandler(str(logfile), maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    if json_mode:
        class JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                data = {
                    "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
                    "level": record.levelname,
                    "logger": record.name,
                    "msg": record.getMessage(),
                }
                return json.dumps(data, ensure_ascii=False)

        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s'))

    logger.addHandler(handler)
    return logger

