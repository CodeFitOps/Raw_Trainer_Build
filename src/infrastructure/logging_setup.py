from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional


def _parse_level(level_name: str) -> int:
    """
    Convert a string like 'DEBUG' or 'info' into a logging level int.

    If the name is unknown, default to INFO.
    """
    name = level_name.strip().upper()
    mapping = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
    }
    return mapping.get(name, logging.INFO)


def configure_logging(
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
    enable_console_logs: bool = False,
) -> None:
    """
    Configure global logging for the application / tools.

    - level:
        Logging level name ("DEBUG", "INFO", ...).
        If None, we look at env var RAWTRAINER_LOG_LEVEL.
        If still None, default to INFO.

    - log_file:
        If provided, we log to this file (in addition to console if enabled).

    - enable_console_logs:
        If True, logs (INFO/DEBUG/...) also go to stdout.
        If False, logs sólo a fichero.
    """
    # 1) Resolver nivel
    if level is None:
        env_level = os.getenv("RAWTRAINER_LOG_LEVEL")
        if env_level:
            level = env_level
        else:
            level = "INFO"

    log_level = _parse_level(level)

    # 2) Root logger global
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Evitar duplicados si se llama varias veces
    root_logger.handlers.clear()

    # 3) Formato común
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 4) Handler de consola (opcional)
    if enable_console_logs:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # 5) Handler de fichero (opcional pero recomendado)
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)