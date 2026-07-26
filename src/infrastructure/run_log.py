# src/infrastructure/run_log.py
"""Persistencia de sesiones de entrenamiento en .run_logs_v2/.

Formato ÚNICO de record para que `stats` cuente tanto las sesiones del runner
descriptivo como las del modo driven. Un fichero JSON por sesión.

Claves que lee stats_v2: workout_name, source_file, started_at, ended_at,
duration_seconds. El resto (stages/jobs/score) es riqueza adicional para
historial y scoring por modo.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.infrastructure.workout_registry import _project_root


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slugify(text: str) -> str:
    text = (text or "").strip().lower()
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in text) or "workout"


def get_logs_dir() -> Path:
    logs_dir = _project_root() / ".run_logs_v2"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def build_run_record_base(
    workout: Any,
    source_path: Optional[Path],
    *,
    mode: str = "descriptive",
) -> Dict[str, Any]:
    """Record base de una sesión. `mode` = 'descriptive' | 'driven'."""
    return {
        "version": 2,
        "session_mode": mode,
        "workout_name": workout.name,
        "workout_description": getattr(workout, "description", None),
        "source_file": str(source_path) if source_path is not None else None,
        "started_at": now_iso(),
        "ended_at": None,
        "duration_seconds": None,
        "stages": [],
        "overall_note": None,
    }


def save_run_record(record: Dict[str, Any]) -> Path:
    logs_dir = get_logs_dir()
    slug = _slugify(record.get("workout_name") or "workout")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S-%f")  # micros -> sin colisión en el mismo segundo
    target = logs_dir / f"{slug}_{ts}.json"
    with target.open("w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return target


def logs_dirs() -> list:
    """Directorios de logs candidatos que existen (canónico + legacy).

    Fuente ÚNICA para localizar logs (la usan el driven scoring y stats_v2),
    resuelta en el momento de la llamada.
    """
    root = _project_root()
    candidates = [
        root / ".run_logs_v2",          # canónico: donde escriben runner y driven
        root / "run-logs-v2",
        root / "run-logs",
        root / "data" / "run-logs-v2",
        root / "data" / "run-logs",
    ]
    out: list = []
    seen = set()
    for d in candidates:
        if d.exists() and d not in seen:
            seen.add(d)
            out.append(d)
    return out


def load_all_records() -> list:
    """Todos los records de sesión (dicts crudos) de las carpetas de logs."""
    records: list = []
    for d in logs_dirs():
        for p in sorted(d.glob("*.json")):
            try:
                records.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                pass
    return records
