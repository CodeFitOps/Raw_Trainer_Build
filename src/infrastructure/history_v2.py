# src/infrastructure/history_v2.py
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from src.infrastructure.workout_registry import _project_root

# Carpeta donde se guardarán los logs de ejecución v2
RUN_LOG_DIR = _project_root() / "data" / "run_logs_v2"


def _ensure_dir() -> None:
    RUN_LOG_DIR.mkdir(parents=True, exist_ok=True)


def _slugify(text: str) -> str:
    """
    Muy simple: minúsculas, espacios -> guiones, solo alfanumérico y '-'.
    """
    import re

    s = (text or "workout").strip().lower()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-]+", "", s)
    return s or "workout"


def _to_serializable(obj: Any) -> Any:
    """
    Pequeño helper por si en el futuro metemos dataclasses u objetos en el run_log.
    """
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, (list, tuple)):
        return [_to_serializable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    return obj


def write_run_log_v2(run_log: Dict[str, Any]) -> Path:
    """
    Guarda un log de ejecución de workout v2 en JSON.

    Esperamos al menos:
      - workout_name (str)
      - started_at (ISO string)
    y opcionalmente:
      - finished_at
      - total_duration_seconds
      - stages[...]{ duration_seconds, note, jobs[...] {...} }
    """
    _ensure_dir()

    workout_name = str(run_log.get("workout_name") or "workout").strip()
    started_at = str(run_log.get("started_at") or "")

    # Si viene ISO -> usamos para el nombre; si no, ahora.
    try:
        dt_start = datetime.fromisoformat(started_at)
    except Exception:
        dt_start = datetime.now()
        run_log["started_at"] = dt_start.isoformat(timespec="seconds")

    slug = _slugify(workout_name)
    ts = dt_start.strftime("%Y%m%d-%H%M%S")

    path = RUN_LOG_DIR / f"{slug}_{ts}.json"

    serializable = _to_serializable(run_log)
    path.write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")

    return path