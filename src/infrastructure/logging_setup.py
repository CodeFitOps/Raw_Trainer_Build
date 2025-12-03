from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def configure_logging(
    *,
    debug: bool = False,
    log_file: Optional[Path] = None,
    log_to_stderr: bool = True,
) -> None:
    """
    Configure global logging for the application.

    Parameters
    ----------
    debug:
        If True, set log level to DEBUG. Otherwise INFO.
    log_file:
        Optional path to a log file. If provided, logs are written there
        (with rotation) in addition to stderr (if log_to_stderr=True).
    log_to_stderr:
        If True, attach a StreamHandler to stderr.
    """
    root = logging.getLogger()

    level = logging.DEBUG if debug else logging.INFO

    # Si ya hay handlers configurados, solo ajustamos niveles y salimos.
    if root.handlers:
        root.setLevel(level)
        for handler in root.handlers:
            handler.setLevel(level)
        return

    root.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)8s] [%(name)s:%(lineno)d] - %(message)s"
    )

    # Handler a stderr
    if log_to_stderr:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level)
        stream_handler.setFormatter(fmt)
        root.addHandler(stream_handler)

    # Handler a fichero (rotativo)
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)