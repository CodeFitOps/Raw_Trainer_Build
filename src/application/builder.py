# src/application/builder.py
"""Lógica (capa de aplicación) del builder de workouts.

Provee al asistente lo que necesita SIN saber de I/O de interfaz, de modo que
la CLI y la futura GUI compartan la misma base:
  - los modos disponibles (a partir de los schemas job.<mode>.schema.json),
  - los campos escalares de cada modo y de sus ejercicios (key, tipo, requerido),
  - el casteo/validación de un valor suelto,
  - la validación del workout completo contra el pipeline (schema + dominio).
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.application.workout_loader import (
    load_workout_v2_model_from_file,
    WorkoutLoadError,
)

# JSON Schema "type" -> nombre de tipo interno del builder
_SCALAR = {"integer": "int", "number": "float", "string": "str", "boolean": "bool"}


def list_modes(schema_root: Path) -> List[str]:
    """Modos disponibles, deducidos de los ficheros job.<mode>.schema.json."""
    modes: List[str] = []
    for p in sorted(schema_root.glob("job.*.schema.json")):
        m = p.name.removeprefix("job.").removesuffix(".schema.json")
        if m:
            modes.append(m)
    return modes


def _read_schema(mode: str, schema_root: Path) -> Optional[Dict[str, Any]]:
    p = schema_root / f"job.{mode}.schema.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _scalar_fields(props: Dict[str, Any], required: set, skip: set) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for key, spec in props.items():
        if key in skip:
            continue
        t = spec.get("type") if isinstance(spec, dict) else None
        if t in _SCALAR:
            out.append({
                "key": key,
                "type": _SCALAR[t],
                "required": key in required,
                "desc": spec.get("description", "") if isinstance(spec, dict) else "",
            })
    # requeridos primero, luego alfabético
    out.sort(key=lambda f: (not f["required"], f["key"]))
    return out


def mode_scalar_fields(mode: str, schema_root: Path) -> List[Dict[str, Any]]:
    """Campos escalares a nivel job para un modo (sin name/mode/exercises)."""
    sch = _read_schema(mode, schema_root)
    if not sch:
        return []
    props = sch.get("properties", {}) or {}
    required = set(sch.get("required", []) or [])
    return _scalar_fields(props, required, skip={"name", "mode", "exercises"})


def exercise_scalar_fields(mode: str, schema_root: Path) -> List[Dict[str, Any]]:
    """Campos escalares de cada ejercicio para un modo (sin name)."""
    sch = _read_schema(mode, schema_root)
    if not sch:
        return []
    items = ((sch.get("properties", {}) or {}).get("exercises", {}) or {}).get("items", {}) or {}
    props = items.get("properties", {}) or {}
    required = set(items.get("required", []) or [])
    return _scalar_fields(props, required, skip={"name"})


def cast_value(raw: str, typ: str) -> Any:
    """Castea un valor de texto al tipo esperado. Lanza ValueError si no encaja."""
    raw = raw.strip()
    if typ == "int":
        return int(raw)
    if typ == "float":
        return float(raw)
    if typ == "bool":
        low = raw.lower()
        if low in ("true", "t", "yes", "y", "s", "si", "sí", "1"):
            return True
        if low in ("false", "f", "no", "n", "0"):
            return False
        raise ValueError("bool")
    return raw  # str


def validate_workout_dict(workout: Dict[str, Any], schema_root: Path) -> Optional[str]:
    """Valida un workout dict con el pipeline real. Devuelve None si es válido,
    o un mensaje de error legible si no lo es."""
    tmp = Path(tempfile.gettempdir()) / "_rt_builder_validate.yaml"
    try:
        tmp.write_text(
            yaml.safe_dump(workout, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        load_workout_v2_model_from_file(path=tmp, schema_root=schema_root)
        return None
    except WorkoutLoadError as exc:
        return str(exc)
    except Exception as exc:  # noqa: BLE001
        return str(exc)
    finally:
        try:
            tmp.unlink()
        except Exception:
            pass
