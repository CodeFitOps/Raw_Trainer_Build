# src/application/workout_loader.py
from __future__ import annotations

from pathlib import Path
from typing import Any
import logging

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

from src.domain.workout_model import Workout
from src.domain.workout_errors import WorkoutError

log = logging.getLogger(__name__)


class WorkoutLoadError(Exception):
    """
    Error de alto nivel para la capa de aplicación al cargar un workout.

    Envuelve errores de IO, YAML, o de dominio (WorkoutError).
    """

    def __init__(self, message: str, *, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


def load_workout_from_file(path: Path) -> Workout:
    """
    Carga un fichero YAML y lo convierte en un Workout de dominio.

    Reglas:
    - Si PyYAML no está instalado -> WorkoutLoadError.
    - Si el fichero no se puede leer -> WorkoutLoadError.
    - Si el YAML no es válido -> WorkoutLoadError.
    - Si el dominio lo considera inválido -> WorkoutLoadError envolviendo WorkoutError.
    """
    if yaml is None:
        msg = "pyyaml is required to load workouts but is not installed."
        log.error(msg)
        raise WorkoutLoadError(msg)

    log.info("Loading workout from file: %s", path)

    try:
        raw_text = path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        msg = f"Cannot read workout file {path}: {exc}"
        log.error(msg)
        raise WorkoutLoadError(msg, cause=exc)

    try:
        data: Any = yaml.safe_load(raw_text)
    except Exception as exc:  # noqa: BLE001
        msg = f"YAML parse error in {path}: {exc}"
        log.error(msg)
        raise WorkoutLoadError(msg, cause=exc)

    log.debug("YAML loaded for %s, top-level type=%s", path, type(data).__name__)

    try:
        workout = Workout.from_dict(data)
    except WorkoutError as exc:
        msg = f"Workout in {path} is invalid according to domain model: {exc}"
        log.error(msg)
        raise WorkoutLoadError(msg, cause=exc)

    log.info(
        "Workout loaded successfully from %s: name=%r stages=%d",
        path,
        workout.name,
        len(workout.stages),
    )
    return workout