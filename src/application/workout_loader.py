# src/application/workout_loader.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from internal_tools.schema_loader_v2 import (
    load_workout_v2 as _load_workout_v2,
    SchemaValidationError,
)
from src.domain_v2.workout_v2 import WorkoutV2

log = logging.getLogger(__name__)


class WorkoutLoadError(Exception):
    """Error de alto nivel para la carga de workouts (CLI, etc.)."""
    pass


def load_workout_v2_from_file(path: Path, schema_root: Path) -> Dict[str, Any]:
    """
    Loader v2 (única vía):
      - Normaliza el vocabulario de MODE y valida el workout contra los
        JSON Schemas (estructura global + cada job por su MODE).
      - Devuelve el dict ya validado.
    """
    log.info("Loading workout (v2) from file: %s", path)
    try:
        data = _load_workout_v2(path=path, schema_root=schema_root)
    except SchemaValidationError as exc:
        msg = f"Workout in {path} is invalid according to JSON Schemas: {exc}"
        log.error(msg)
        raise WorkoutLoadError(msg) from exc
    return data


def load_workout_v2_model_from_file(path: Path, schema_root: Path) -> WorkoutV2:
    """
    Valida el YAML y construye el modelo de dominio tipado WorkoutV2.
    """
    data = load_workout_v2_from_file(path=path, schema_root=schema_root)
    return WorkoutV2.from_dict(data)
