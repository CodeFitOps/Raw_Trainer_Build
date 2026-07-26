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
        root / ".run_logs_v2",          # donde escribe run-v2 (canónico)
        root / "run-logs-v2",
        root / "run-logs",
        root / "data" / "run-logs-v2",
        root / "data" / "run-logs",
    ]

    for c in candidates:
        if c.exists():
            return c

    # fallback: creamos el canónico (el mismo que usa run-v2)
    fallback = root / ".run_logs_v2"
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


def _existing_logs_dirs() -> List[Path]:
    """Directorios de logs existentes. Fuente única: run_log.logs_dirs()."""
    from src.infrastructure import run_log
    return run_log.logs_dirs()


def iter_run_log_paths(logs_dir: Optional[Path] = None) -> Iterable[Path]:
    """
    Paths de todos los .json de logs, ordenados por mtime descendente.

    Sin `logs_dir`, se AGREGAN todos los directorios candidatos que existan
    (canónico .run_logs_v2 + legacy), resueltos en el momento de la llamada,
    de modo que siempre se incluye la carpeta donde acaba de escribirse una
    sesión aunque no existiera al importar el módulo.
    """
    if logs_dir is not None:
        bases = [logs_dir] if logs_dir.exists() else []
    else:
        bases = _existing_logs_dirs()

    files: List[Path] = []
    for base in bases:
        files.extend(p for p in base.iterdir() if p.is_file() and p.suffix == ".json")
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
    # Acepta las claves reales de run-v2 (ended_at / duration_seconds)
    finished_at = _parse_iso(raw.get("finished_at") or raw.get("ended_at"))

    total_dur = raw.get("total_duration_seconds")
    if not isinstance(total_dur, (int, float)):
        total_dur = raw.get("duration_seconds")
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


# ---------------------------------------------------------------------------
# PRs / marcas por job (a partir de los scores capturados en modo driven)
# ---------------------------------------------------------------------------

@dataclass
class PRSummary:
    workout_name: str
    job_name: str
    score_key: str
    unit: str
    higher_better: bool
    best: float
    attempts: int
    last: float


# (score_key, higher_better, unidad)
_SCORE_KEYS = [
    ("result_time_seconds", False, "tiempo"),   # for_time: menos es mejor
    ("result_total_reps", True, "reps"),         # edt: densidad
    ("result_rounds", True, "rondas"),           # amrap / death-by
]


def collect_prs(records: Iterable[dict]) -> List[PRSummary]:
    """Agrupa los scores por (workout, job, score_key) y calcula la mejor marca."""
    agg: Dict[tuple, PRSummary] = {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        wname = str(rec.get("workout_name") or "?")
        for stage in rec.get("stages", []) or []:
            if not isinstance(stage, dict):
                continue
            for job in stage.get("jobs", []) or []:
                if not isinstance(job, dict):
                    continue
                jname = str(job.get("name") or "?")
                for key, higher_better, unit in _SCORE_KEYS:
                    v = job.get(key)
                    if not isinstance(v, (int, float)) or isinstance(v, bool):
                        continue
                    k = (wname, jname, key)
                    cur = agg.get(k)
                    if cur is None:
                        agg[k] = PRSummary(wname, jname, key, unit, higher_better, v, 1, v)
                    else:
                        cur.attempts += 1
                        cur.last = v
                        if (higher_better and v > cur.best) or (
                            not higher_better and v < cur.best
                        ):
                            cur.best = v
    return sorted(
        agg.values(), key=lambda p: (p.workout_name.lower(), p.job_name.lower())
    )


def _fmt_pr_best(pr: PRSummary) -> str:
    if pr.score_key == "result_time_seconds":
        return _fmt_seconds(pr.best)
    return f"{int(pr.best)} {pr.unit}"


def format_pr_table(prs: List[PRSummary]) -> str:
    if not prs:
        return ""
    lines: List[str] = ["", "🏆 Marcas (PRs)"]
    header = f"{'Workout':<26}  {'Job':<22}  {'Mejor':>12}  {'Intentos':>8}"
    lines.append(header)
    lines.append("-" * len(header))
    for pr in prs:
        lines.append(
            f"{pr.workout_name[:26]:<26}  {pr.job_name[:22]:<22}  "
            f"{_fmt_pr_best(pr):>12}  {pr.attempts:>8}"
        )
    return "\n".join(lines)


def build_pr_report(logs_dir: Optional[Path] = None) -> str:
    """Sección de marcas/PRs lista para imprimir ('' si no hay scores)."""
    from src.infrastructure import run_log
    return format_pr_table(collect_prs(run_log.load_all_records()))