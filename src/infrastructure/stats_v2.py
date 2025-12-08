# src/infrastructure/stats_v2.py
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from src.infrastructure.workout_registry import _project_root


# ---------------------------------------------------------------------------
# Localización de logs
# ---------------------------------------------------------------------------

def _detect_logs_dir() -> Path:
    """
    Intenta localizar el directorio donde se están guardando los logs de run-v2.
    Probamos varios nombres razonables y si no existe ninguno, devolvemos
    `<project_root>/run-logs-v2` (creándolo).
    """
    root = _project_root()
    candidates = [
        root / "run-logs-v2",
        root / "run-logs",
        root / "data" / "run-logs-v2",
        root / "data" / "run-logs",
    ]

    for c in candidates:
        if c.exists():
            return c

    # fallback: creamos uno nuevo
    fallback = root / "run-logs-v2"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


RUN_LOGS_DIR: Path = _detect_logs_dir()


# ---------------------------------------------------------------------------
# Modelos de stats (simples, para lectura)
# ---------------------------------------------------------------------------

@dataclass
class WorkoutRunSummary:
    """
    Resumen de UNA ejecución concreta de un workout.
    """
    workout_name: str
    source_file: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    total_duration_seconds: Optional[float]


@dataclass
class WorkoutStats:
    """
    Stats agregadas por workout_name.
    """
    workout_name: str
    total_sessions: int
    last_session_at: Optional[datetime]
    avg_duration_seconds: Optional[float]
    min_duration_seconds: Optional[float]
    max_duration_seconds: Optional[float]


# ---------------------------------------------------------------------------
# Carga de logs
# ---------------------------------------------------------------------------

def _parse_iso(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str or not isinstance(dt_str, str):
        return None
    try:
        # compatible con ISO básico "YYYY-MM-DDTHH:MM:SS"
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None


def iter_run_log_paths(logs_dir: Optional[Path] = None) -> Iterable[Path]:
    """
    Devuelve los paths de todos los .json de logs, ordenados por mtime descendente.
    """
    base = logs_dir or RUN_LOGS_DIR
    if not base.exists():
        return []

    files = [p for p in base.iterdir() if p.is_file() and p.suffix == ".json"]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def load_run_log(path: Path) -> Optional[WorkoutRunSummary]:
    """
    Carga un JSON de run y devuelve un resumen normalizado.
    Si el fichero está corrupto o no es un dict, devuelve None.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(raw, dict):
        return None

    workout_name = str(raw.get("workout_name") or raw.get("name") or "UNKNOWN")
    source_file = raw.get("source_file") or raw.get("workout_file")

    started_at = _parse_iso(raw.get("started_at"))
    finished_at = _parse_iso(raw.get("finished_at"))

    total_dur = raw.get("total_duration_seconds")
    if isinstance(total_dur, (int, float)):
        total_duration = float(total_dur)
    else:
        total_duration = None

    return WorkoutRunSummary(
        workout_name=workout_name,
        source_file=source_file,
        started_at=started_at,
        finished_at=finished_at,
        total_duration_seconds=total_duration,
    )


def load_all_runs(logs_dir: Optional[Path] = None) -> List[WorkoutRunSummary]:
    summaries: List[WorkoutRunSummary] = []
    for path in iter_run_log_paths(logs_dir):
        summary = load_run_log(path)
        if summary is not None:
            summaries.append(summary)
    return summaries


# ---------------------------------------------------------------------------
# Agregación de stats
# ---------------------------------------------------------------------------

def compute_stats_per_workout(
    runs: Iterable[WorkoutRunSummary],
) -> List[WorkoutStats]:
    """
    Agrupa los runs por workout_name y calcula stats agregadas simples.
    """
    grouped: Dict[str, List[WorkoutRunSummary]] = {}

    for run in runs:
        grouped.setdefault(run.workout_name, []).append(run)

    stats_list: List[WorkoutStats] = []

    for workout_name, ws in grouped.items():
        # filtramos runs con duración válida
        durations = [
            r.total_duration_seconds
            for r in ws
            if isinstance(r.total_duration_seconds, (int, float))
        ]

        if durations:
            total_sessions = len(ws)
            avg_dur = sum(durations) / len(durations)
            min_dur = min(durations)
            max_dur = max(durations)
        else:
            total_sessions = len(ws)
            avg_dur = min_dur = max_dur = None

        # Última sesión por fecha de inicio; si no hay, None
        valid_dates = [r.started_at for r in ws if r.started_at is not None]
        last_session_at = max(valid_dates) if valid_dates else None

        stats_list.append(
            WorkoutStats(
                workout_name=workout_name,
                total_sessions=total_sessions,
                last_session_at=last_session_at,
                avg_duration_seconds=avg_dur,
                min_duration_seconds=min_dur,
                max_duration_seconds=max_dur,
            )
        )

    # Ordenamos por nombre para salida estable
    stats_list.sort(key=lambda s: s.workout_name.lower())
    return stats_list


# ---------------------------------------------------------------------------
# Helper para CLI: formateo
# ---------------------------------------------------------------------------

def _fmt_seconds(seconds: Optional[float]) -> str:
    if seconds is None or math.isnan(seconds):
        return "-"
    seconds = int(round(seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    if m > 0:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def format_stats_table(stats: List[WorkoutStats]) -> str:
    """
    Devuelve una tabla en texto plano con las stats por workout_name.
    """
    if not stats:
        return "No run history found yet (v2)."

    lines: List[str] = []
    header = f"{'#':>2}  {'Workout':<40}  {'Sessions':>8}  {'Last run':<19}  {'Avg':>10}  {'Min':>10}  {'Max':>10}"
    lines.append(header)
    lines.append("-" * len(header))

    for idx, st in enumerate(stats, start=1):
        last = st.last_session_at.isoformat(sep=" ", timespec="seconds") if st.last_session_at else "-"
        avg = _fmt_seconds(st.avg_duration_seconds)
        min_ = _fmt_seconds(st.min_duration_seconds)
        max_ = _fmt_seconds(st.max_duration_seconds)

        lines.append(
            f"{idx:>2}  {st.workout_name[:40]:<40}  {st.total_sessions:>8}  {last:<19}  {avg:>10}  {min_:>10}  {max_:>10}"
        )

    return "\n".join(lines)


def build_stats_report(logs_dir: Optional[Path] = None) -> str:
    """
    Punto de entrada sencillo para la CLI:
    lee todos los runs y devuelve una tabla lista para imprimir.
    """
    runs = load_all_runs(logs_dir=logs_dir)
    stats = compute_stats_per_workout(runs)
    return format_stats_table(stats)