# src/application/workout_loader.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Iterator

import yaml

from src.domain.workout_model import Workout
from src.domain.workout_errors import WorkoutTopLevelValidationError

# Nuevo loader basado en JSON Schema (v2 pipeline)
from internal_tools.schema_loader_v2 import (
    load_workout_v2 as _load_workout_v2,
    SchemaValidationError,
)

from src.domain_v2.workout_v2 import WorkoutV2  # dominio v2

log = logging.getLogger(__name__)


class WorkoutLoadError(Exception):
    """Error de alto nivel para la carga de workouts (CLI, etc.)."""
    pass


# ---------------------------------------------------------------------------
# Utilidades comunes
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkoutLoadError(f"Cannot read workout file {path}: {exc}") from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise WorkoutLoadError(f"YAML syntax error in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise WorkoutLoadError(
            f"Workout in {path} must be a mapping/object at top level"
        )

    return data


# ---------------------------------------------------------------------------
# Loader v1 (dominio actual)
# ---------------------------------------------------------------------------


def load_workout_from_file(path: Path) -> Workout:
    """
    Loader v1: usa las dataclasses actuales (Workout / Stage / Job / Exercise).

    Se mantiene tal cual para no romper nada del CLI actual.
    """
    log.info("Loading workout from file: %s", path)

    data = _load_yaml(path)

    try:
        workout = Workout.from_dict(data)
    except WorkoutTopLevelValidationError as exc:
        msg = f"Workout in {path} is invalid according to domain model: {exc}"
        log.error(msg)
        raise WorkoutLoadError(msg) from exc

    log.info(
        "Workout loaded successfully from %s: name=%r stages=%d",
        path,
        getattr(workout, "name", "<no-name>"),
        len(getattr(workout, "stages", [])),
    )
    return workout


# ---------------------------------------------------------------------------
# Normalización de MODE para v2
# ---------------------------------------------------------------------------

# Modo canónico interno por cada variante que aceptamos en YAML v2
_MODE_SYNONYMS_V2: dict[str, str] = {
    # CUSTOM / custom_sets
    "CUSTOM": "custom_sets",
    "CUSTOM_SETS": "custom_sets",
    "custom_sets": "custom_sets",
    "custom": "custom_sets",

    # TABATA
    "TABATA": "TABATA",
    "tabata": "TABATA",

    # EMOM
    "EMOM": "EMOM",
    "emom": "EMOM",

    # AMRAP
    "AMRAP": "AMRAP",
    "amrap": "AMRAP",

    # FOR_TIME
    "FOR_TIME": "FOR_TIME",
    "for_time": "FOR_TIME",

    # EDT
    "EDT": "EDT",
    "edt": "EDT",
}

# Conjunto de modos soportados a nivel de YAML (antes de normalizar)
_SUPPORTED_MODES_V2: set[str] = set(_MODE_SYNONYMS_V2.keys())


def _iter_jobs_nodes(raw_workout: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """
    Itera todos los nodos "job" del dict YAML ya cargado:
    raw["STAGES"][i]["JOBS"][j]
    Ignora cosas raras que no sean dicts.
    """
    stages = raw_workout.get("STAGES") or raw_workout.get("stages") or []
    if not isinstance(stages, list):
        return

    for stage in stages:
        if not isinstance(stage, dict):
            continue
        jobs = stage.get("JOBS") or stage.get("jobs") or []
        if not isinstance(jobs, list):
            continue
        for job in jobs:
            if isinstance(job, dict):
                yield job


def _validate_and_normalize_modes_v2(raw_workout: Dict[str, Any]) -> None:
    """
    Paso v2:
    - Comprueba que todos los MODE son soportados.
    - Normaliza in-place a su valor canónico (p.ej. CUSTOM -> custom_sets).

    Si encuentra un modo desconocido, lanza WorkoutLoadError.
    """
    for job in _iter_jobs_nodes(raw_workout):
        raw_mode = job.get("MODE")
        name = job.get("NAME") or job.get("name") or "?"

        if not isinstance(raw_mode, str) or not raw_mode.strip():
            raise WorkoutLoadError(
                f"Job {name!r} is missing MODE or it is not a string"
            )

        mode_key = raw_mode.strip()
        # Primero miramos tal cual, luego en mayúsculas para tolerar for_time/edt/etc.
        if (
            mode_key not in _SUPPORTED_MODES_V2
            and mode_key.upper() not in _SUPPORTED_MODES_V2
        ):
            raise WorkoutLoadError(
                f"Unsupported MODE {raw_mode!r} in job {name!r}"
            )

        # Normalización al canónico
        canon = _MODE_SYNONYMS_V2.get(mode_key) or _MODE_SYNONYMS_V2.get(
            mode_key.upper()
        )
        if canon:
            job["MODE"] = canon
        else:
            # Por diseño no deberíamos llegar aquí porque hemos validado antes,
            # pero por si acaso dejamos el original.
            job["MODE"] = mode_key


# ---------------------------------------------------------------------------
# Loader v2 (JSON Schema first)
# ---------------------------------------------------------------------------


def load_workout_v2_from_file(path: Path, schema_root: Path) -> Dict[str, Any]:
    """
    Loader v2: delega en internal_tools.schema_loader_v2.load_workout_v2,
    que:
      - Valida el workout completo contra workout.schema.json
      - Valida cada job contra su schema por MODE
      - Devuelve un dict ya válido.

    Aquí sólo envolvemos errores a WorkoutLoadError.
    """
    log.info(
        "Loading workout (v2) from file: %s with schema_root=%s",
        path,
        schema_root,
    )

    try:
        data = _load_workout_v2(path=path, schema_root=schema_root)
    except SchemaValidationError as exc:
        msg = f"Workout in {path} is invalid according to JSON Schemas: {exc}"
        log.error(msg)
        raise WorkoutLoadError(msg) from exc

    # Normalización adicional de MODE (soportar CUSTOM, for_time, etc.)
    _validate_and_normalize_modes_v2(data)

    return data


def load_workout_v2_model_from_file(path: Path, schema_root: Path) -> WorkoutV2:
    """
    Atajo v2:
      - Valida el YAML con JSON Schemas (top-level + jobs por MODE)
      - Normaliza MODE (CUSTOM -> custom_sets, etc.)
      - Construye y devuelve un WorkoutV2 de dominio.
    """
    data = load_workout_v2_from_file(path=path, schema_root=schema_root)
    return WorkoutV2.from_dict(data)