# internal_tools/schema_loader_v2.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

import yaml
from jsonschema import Draft7Validator, ValidationError

__all__ = [
    "SchemaValidationError",
    "validate_instance_against_schema",
    "load_workout_v2",
]

# ---------------------------------------------------------------------------
# Excepción de alto nivel para la capa de schemas
# ---------------------------------------------------------------------------


class SchemaValidationError(Exception):
    """Error de validación de JSON Schema con contexto legible."""

    pass


# ---------------------------------------------------------------------------
# Helpers genéricos
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SchemaValidationError(f"Cannot read YAML file {path}: {exc}") from exc

    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise SchemaValidationError(f"YAML syntax error in {path}: {exc}") from exc


def _load_json_schema(schema_path: Path) -> Dict[str, Any]:
    try:
        text = schema_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise SchemaValidationError(
            f"Cannot read JSON Schema file {schema_path}: {exc}"
        ) from exc

    try:
        schema = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SchemaValidationError(
            f"JSON error in schema file {schema_path}: {exc}"
        ) from exc

    if not isinstance(schema, Mapping):
        raise SchemaValidationError(f"Schema {schema_path} must be a JSON object")

    return dict(schema)


def validate_instance_against_schema(
    *, instance: Any, schema_path: Path, context: str = ""
) -> None:
    """
    Valida un objeto (dict/list/etc.) contra un JSON Schema.

    Lanza SchemaValidationError con un mensaje limpio si falla.
    """
    schema = _load_json_schema(schema_path)

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)

    if not errors:
        return

    # De momento devolvemos solo el primer error, pero con info suficiente.
    first: ValidationError = errors[0]

    path_str = "/".join(str(p) for p in first.path) or "<root>"
    base_msg = f"{schema_path.name}: at {path_str}: {first.message}"

    if context:
        msg = f"{context}: {base_msg}"
    else:
        msg = base_msg

    raise SchemaValidationError(msg)


# ---------------------------------------------------------------------------
# Validación por MODE (job-level)
# ---------------------------------------------------------------------------

# Mapea cada MODE (normalizado a lower) al schema específico de job
JOB_MODE_SCHEMAS: Dict[str, str] = {
    "custom_sets": "job.custom_sets.schema.json",
    "tabata": "job.tabata.schema.json",
    "emom": "job.emom.schema.json",
    "amrap": "job.amrap.schema.json",
    "for_time": "job.for_time.schema.json",
    "edt": "job.edt.schema.json",
}


def _validate_jobs_against_mode_schemas(
    workout_dict: Dict[str, Any], *, schema_root: Path
) -> None:
    """
    Recorre STAGES/JOBS de un workout dict y valida cada job contra
    su JSON Schema específico según MODE.
    """
    stages = workout_dict.get("STAGES") or workout_dict.get("stages") or []
    if not isinstance(stages, list):
        # Esto ya debería estar controlado por workout.schema.json,
        # pero por si acaso.
        raise SchemaValidationError("Workout STAGES must be a list for job validation")

    for s_idx, stage in enumerate(stages, start=1):
        if not isinstance(stage, dict):
            raise SchemaValidationError(
                f"Stage {s_idx}: stage must be an object for job validation"
            )

        jobs = stage.get("JOBS") or stage.get("jobs") or []
        if not isinstance(jobs, list):
            raise SchemaValidationError(
                f"Stage {s_idx}: JOBS must be a list for job validation"
            )

        for j_idx, job in enumerate(jobs, start=1):
            if not isinstance(job, dict):
                raise SchemaValidationError(
                    f"Stage {s_idx}, job {j_idx}: job must be an object"
                )

            mode_raw = job.get("MODE")
            if not isinstance(mode_raw, str):
                raise SchemaValidationError(
                    f"Stage {s_idx}, job {j_idx}: MODE must be a string "
                    f"for job schema validation"
                )

            mode_key = mode_raw.strip().lower()
            schema_filename = JOB_MODE_SCHEMAS.get(mode_key)
            if not schema_filename:
                raise SchemaValidationError(
                    f"Stage {s_idx}, job {j_idx}: unsupported MODE {mode_raw!r} "
                    f"for job schema validation"
                )

            job_schema_path = schema_root / schema_filename

            validate_instance_against_schema(
                instance=job,
                schema_path=job_schema_path,
                context=f"Stage {s_idx}, job {j_idx}, mode={mode_raw!r}",
            )


# ---------------------------------------------------------------------------
# API principal para el loader v2
# ---------------------------------------------------------------------------


def load_workout_v2(path: Path, schema_root: Path) -> Dict[str, Any]:
    """
    Carga un workout YAML como dict y lo valida en dos pasos:

    1. Contra workout.schema.json (estructura global: NAME, STAGES, etc.)
    2. Cada JOB contra su schema específico según MODE (custom_sets, TABATA, EMOM, ...)

    De momento devuelve el dict "crudo" ya validado. La capa de dominio v2
    construirá las dataclasses encima.
    """
    workout_dict = _load_yaml(path)

    if not isinstance(workout_dict, dict):
        raise SchemaValidationError(
            f"{path}: workout top-level must be a mapping/object"
        )

    # 1) Validación top-level
    workout_schema_path = schema_root / "workout.schema.json"
    validate_instance_against_schema(
        instance=workout_dict,
        schema_path=workout_schema_path,
        context=str(path),
    )

    # 2) Validación por MODE
    _validate_jobs_against_mode_schemas(workout_dict, schema_root=schema_root)

    return workout_dict