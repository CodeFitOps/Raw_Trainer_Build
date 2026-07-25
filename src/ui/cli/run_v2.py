# src/ui/cli/run_v2.py
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.domain_v2.workout_v2 import WorkoutV2
from src.infrastructure.workout_registry import _project_root
from src.ui.cli.style import (
    title,
    stage_title,
    job_title,
    workout_label,
    stage_label,
    job_label,
    info,
    success,
    prompt,
)

IND = "   "          # sangría base de un job
BAR = 46             # ancho del separador de job


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slugify(text: str) -> str:
    text = text.strip().lower()
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in text) or "workout"


def _get_logs_dir() -> Path:
    root = _project_root()
    logs_dir = root / ".run_logs_v2"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


# ---------------------------------------------------------------------------
# Presentación de la ficha de cada job (modo DESCRIPTIVO)
# ---------------------------------------------------------------------------

def _exercise_value(ex) -> str:
    """Prescripción de un ejercicio: reps o tiempo (+ peso)."""
    if getattr(ex, "reps", None) is not None:
        val = f"{ex.reps} reps"
    elif getattr(ex, "work_time_in_seconds", None) is not None:
        val = f"{ex.work_time_in_seconds} s"
    else:
        val = "—"
    if getattr(ex, "weight", None) is not None:
        val += f"  @ {ex.weight:g} kg"
    return val


def _print_job_card(job, index: int, total: int) -> None:
    """Ficha legible de un job: cabecera + prescripción + ejercicios alineados."""
    # --- Cabecera con separador ---
    head = f"── Job {index}/{total} "
    print()
    print(IND + job_title(head + "─" * max(0, BAR - len(head))))
    print(IND + job_title(job.name) + "   " + info(f"[{job.mode.mode_label()}]"))
    if job.description:
        print(IND + info(job.description))
    print()

    # --- Prescripción, en líneas agrupadas y etiquetadas ---
    top = []
    if job.rounds is not None:
        top.append(job_label("Rondas: ") + info(str(job.rounds)))
    if job.cadence:
        top.append(job_label("Cadencia: ") + info(job.cadence))
    if top:
        print(IND + "     ".join(top))

    tiempo = []
    if job.work_time_in_seconds is not None:
        tiempo.append(f"trabajo {job.work_time_in_seconds}s")
    if job.work_time_in_minutes is not None:
        tiempo.append(f"ventana {job.work_time_in_minutes} min")
    if job.rest_time_in_seconds is not None:
        tiempo.append(f"descanso {job.rest_time_in_seconds}s")
    if tiempo:
        print(IND + job_label("Tiempo:   ") + info(" · ".join(tiempo)))

    descanso = []
    if job.rest_between_exercises_in_seconds is not None:
        descanso.append(f"{job.rest_between_exercises_in_seconds}s entre ejercicios")
    if job.rest_between_rounds_in_seconds is not None:
        descanso.append(f"{job.rest_between_rounds_in_seconds}s entre rondas")
    if descanso:
        print(IND + job_label("Descanso: ") + info(" · ".join(descanso)))

    tecnica = []
    if job.eccentric_neg:
        tecnica.append("Excéntrico (NEG)")
    if job.isometric_hold:
        tecnica.append("Isométrico (HOLD)")
    if tecnica:
        print(IND + job_label("Técnica:  ") + info(" · ".join(tecnica)))

    # --- Ejercicios en columna alineada ---
    exs = list(job.exercises or [])
    print()
    print(IND + job_label("Ejercicios"))
    if not exs:
        print(IND + "  " + info("(sin ejercicios)"))
    width = min(max((len(e.name) for e in exs), default=0), 32)
    for i, ex in enumerate(exs, start=1):
        name = ex.name if len(ex.name) <= 32 else ex.name[:31] + "…"
        print(f"{IND}  {i:>2}. " + info(name.ljust(width)) + "    " + success(_exercise_value(ex)))
    print()


# ---------------------------------------------------------------------------
# Registro de la sesión
# ---------------------------------------------------------------------------

def _build_run_record_base(workout: WorkoutV2, source_path: Optional[Path]) -> Dict[str, Any]:
    return {
        "version": 2,
        "workout_name": workout.name,
        "workout_description": workout.description,
        "source_file": str(source_path) if source_path is not None else None,
        "started_at": _now_iso(),
        "ended_at": None,
        "duration_seconds": None,
        "stages": [],
        "overall_note": None,
    }


def _save_run_record(record: Dict[str, Any]) -> Path:
    logs_dir = _get_logs_dir()
    slug = _slugify(record.get("workout_name") or "workout")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = logs_dir / f"{slug}_{ts}.json"
    with target.open("w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return target


# ---------------------------------------------------------------------------
# Runner interactivo (modo descriptivo: avance manual con ENTER)
# ---------------------------------------------------------------------------

def run_workout_v2_interactive(
    workout: WorkoutV2,
    *,
    source_path: Optional[Path] = None,
) -> None:
    run_record = _build_run_record_base(workout, source_path)

    print()
    print(title(f"▶  {workout.name}"))
    if workout.description:
        print(info(workout.description))
    print(workout_label("Stages: ") + info(str(len(workout.stages))))
    print()
    input(prompt("Pulsa ENTER para empezar…"))

    workout_start_ts = time.time()

    for s_idx, stage in enumerate(workout.stages, start=1):
        print()
        print(stage_title(f"═══  Stage {s_idx}/{len(workout.stages)}: {stage.name}  ═══"))
        if stage.description:
            print(stage_label(stage.description))
        input(prompt("Pulsa ENTER para empezar el stage…"))

        stage_start_ts = time.time()
        stage_record: Dict[str, Any] = {
            "index": s_idx,
            "name": stage.name,
            "description": stage.description,
            "duration_seconds": None,
            "note": None,
            "jobs": [],
        }

        for j_idx, job in enumerate(stage.jobs, start=1):
            _print_job_card(job, j_idx, len(stage.jobs))

            input(IND + prompt("ENTER para empezar el job…"))
            job_start_ts = time.time()
            input(IND + prompt("ENTER cuando termines…"))
            job_duration = int(time.time() - job_start_ts)
            print(IND + info(f"⏱  {job_duration}s"))
            job_note = input(IND + prompt("Nota (ENTER para saltar): ")).strip()

            stage_record["jobs"].append(
                {
                    "index": j_idx,
                    "name": job.name,
                    "mode": job.mode.value,
                    "duration_seconds": job_duration,
                    "note": job_note or None,
                }
            )

        stage_duration = int(time.time() - stage_start_ts)
        print()
        print(stage_label(f"Stage completado · {stage_duration}s"))
        stage_note = input("Nota del stage (ENTER para saltar): ").strip()
        stage_record["duration_seconds"] = stage_duration
        stage_record["note"] = stage_note or None
        run_record["stages"].append(stage_record)

    total_duration = int(time.time() - workout_start_ts)
    print()
    print(success(f"✅  Workout terminado — tiempo total: {total_duration}s"))
    overall_note = input("Nota final del workout (ENTER para saltar): ").strip()

    run_record["ended_at"] = _now_iso()
    run_record["duration_seconds"] = total_duration
    run_record["overall_note"] = overall_note or None

    target = _save_run_record(run_record)
    print(info(f"Sesión guardada en {target.name}"))
