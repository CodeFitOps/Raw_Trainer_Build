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
    root = logging.getLogger()

    # Root: deja pasar todo; filtramos por handler
    root_level = logging.DEBUG
    root.setLevel(root_level)

    file_level = logging.DEBUG if debug else logging.INFO
    # Consola: por defecto NO spam (solo warnings+)
    stderr_level = logging.WARNING if not debug else logging.INFO
    # Si quieres cero consola incluso warnings, pon CRITICAL aquí:
    # stderr_level = logging.CRITICAL + 1

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)8s] [%(name)s:%(lineno)d] - %(message)s"
    )

    # Si ya hay handlers configurados, ajustamos niveles de forma inteligente
    if root.handlers:
        for h in root.handlers:
            if isinstance(h, logging.StreamHandler):
                h.setLevel(stderr_level)
            else:
                # File/RotatingFile/otros
                h.setLevel(file_level)
        return

    # Handler a stderr
    if log_to_stderr:
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(stderr_level)
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
        file_handler.setLevel(file_level)
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)