# src/ui/cli/run_v2.py
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

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
# Presentación de la "receta" de cada job (modo DESCRIPTIVO)
# ---------------------------------------------------------------------------

def _fmt_exercise(ex) -> str:
    parts = []
    if getattr(ex, "reps", None) is not None:
        parts.append(f"{ex.reps} reps")
    if getattr(ex, "work_time_in_seconds", None) is not None:
        parts.append(f"{ex.work_time_in_seconds}s")
    if getattr(ex, "weight", None) is not None:
        parts.append(f"@ {ex.weight:g} kg")
    return f"{ex.name}" + (("  —  " + " · ".join(parts)) if parts else "")


def _print_job_details(job) -> None:
    """Imprime la prescripción completa del job + sus ejercicios.

    Es el 'modo descriptivo': todo lo que el atleta necesita saber para
    ejecutar el bloque (rondas, descansos, cadencia, flags y ejercicios).
    """
    meta = []
    if job.rounds is not None:
        meta.append(f"{job.rounds} rondas")
    if job.work_time_in_seconds is not None:
        meta.append(f"trabajo {job.work_time_in_seconds}s")
    if job.work_time_in_minutes is not None:
        meta.append(f"ventana {job.work_time_in_minutes} min")
    if job.rest_time_in_seconds is not None:
        meta.append(f"descanso {job.rest_time_in_seconds}s")
    if job.rest_between_exercises_in_seconds is not None:
        meta.append(f"descanso e/ejercicios {job.rest_between_exercises_in_seconds}s")
    if job.rest_between_rounds_in_seconds is not None:
        meta.append(f"descanso e/rondas {job.rest_between_rounds_in_seconds}s")
    if job.cadence:
        meta.append(f"cadencia {job.cadence}")
    if job.eccentric_neg:
        meta.append("excéntrico (NEG)")
    if job.isometric_hold:
        meta.append("isométrico (HOLD)")

    if meta:
        print("    " + info(" · ".join(meta)))
    print("    " + job_label("Ejercicios:"))
    if not job.exercises:
        print("      " + info("(sin ejercicios)"))
    for ex in job.exercises:
        print("      • " + info(_fmt_exercise(ex)))


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

    print(title(f"Running workout (v2): {workout.name}"))
    if workout.description:
        print(f"{workout_label('Description:')} {info(workout.description)}")
    print(f"{workout_label('Stages:')} {info(str(len(workout.stages)))}")
    print()
    input(prompt("Press ENTER to start workout..."))

    workout_start_ts = time.time()

    for s_idx, stage in enumerate(workout.stages, start=1):
        print()
        print(stage_title(f"Stage {s_idx}: {stage.name}"))
        if stage.description:
            print("  " + f"{stage_label('Description:')} {info(stage.description)}")
        print()
        input("  Press ENTER to start this stage...")

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
            print()
            print(job_title(f"  Job {j_idx}: {job.name} [{job.mode.mode_label()}]"))
            if job.description:
                print("    " + f"{job_label('Desc:')} {info(job.description)}")
            _print_job_details(job)
            print()

            input("    Press ENTER to start this job...")
            job_start_ts = time.time()
            input("    Press ENTER when you finish this job...")
            job_duration = int(time.time() - job_start_ts)
            print()
            print("    Job duration:", info(f"{job_duration}s"))
            job_note = input(prompt("Optional note for this job (ENTER to skip): ")).strip()

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
        print("  Stage duration:", info(f"{stage_duration}s"))
        stage_note = input("  Optional note for this stage (ENTER to skip): ").strip()
        stage_record["duration_seconds"] = stage_duration
        stage_record["note"] = stage_note or None
        run_record["stages"].append(stage_record)

    total_duration = int(time.time() - workout_start_ts)
    print()
    print(success(f"Workout finished! Total time: {total_duration}s"))
    overall_note = input("Final overall note for this workout (ENTER to skip): ").strip()

    run_record["ended_at"] = _now_iso()
    run_record["duration_seconds"] = total_duration
    run_record["overall_note"] = overall_note or None

    target = _save_run_record(run_record)
    print()
    print(info(f"Run saved to {target}"))
