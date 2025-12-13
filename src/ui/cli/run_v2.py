# src/ui/cli/run_v2.py
from __future__ import annotations

import json
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

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
    """
    Very small slug helper for filenames.
    """
    text = text.strip().lower()
    return "".join(
        c if c.isalnum() or c in ("-", "_") else "_"
        for c in text
    ) or "workout"


def _get_logs_dir() -> Path:
    """
    Where we store v2 run logs.

    - Local
    - Fácil de ignorar en git (añade '.run_logs_v2/' a .gitignore).
    """
    root = _project_root()
    logs_dir = root / ".run_logs_v2"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def _build_run_record_base(
    workout: WorkoutV2,
    source_path: Optional[Path],
) -> Dict[str, Any]:
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
    filename = f"{slug}_{ts}.json"
    target = logs_dir / filename

    with target.open("w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    return target


def run_workout_v2_interactive(
    workout: WorkoutV2,
    *,
    source_path: Optional[Path] = None,
) -> None:
    """
    Modo RUN básico para dominio v2:

    - Usa WorkoutV2 (ya validado por JSON Schema).
    - Pausas por workout, stage y job (ENTER).
    - Mide tiempos:
        - total workout
        - cada stage
        - cada job
    - Pide notas opcionales por job, por stage y una nota final.
    - Guarda todo en .run_logs_v2/*.json
    """

    # --- Cabecera + estructura base del log ---
    run_record: Dict[str, Any] = _build_run_record_base(workout, source_path)

    print(title(f"Running workout (v2): {workout.name}"))
    if workout.description:
        print(f"{workout_label('Description:')} {info(workout.description)}")
    print(f"{workout_label('Stages:')} {info(str(len(workout.stages)))}")
    print()

    input(prompt("Press ENTER to start workout..."))

    workout_start_ts = time.time()

    # ------------------------------------------------------------------
    # Recorremos stages y jobs, midiendo tiempos y recogiendo notas
    # ------------------------------------------------------------------
    for s_idx, stage in enumerate(workout.stages, start=1):
        print()
        print(stage_title(f"Stage {s_idx}: {stage.name}"))
        if stage.description:
            print(
                "  "
                + f"{stage_label('Description:')} {info(stage.description)}"
            )
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
            print(job_title(f"  Job {j_idx}: {job.name} [mode={job.mode.value}]"))
            if job.description:
                print(
                    "    "
                    + f"{job_label('Desc:')} {info(job.description)}"
                )

            # Resumen rápido según MODE (simple, sin lógica hardcore)
            if getattr(job, "rounds", None) is not None:
                print(
                    "    "
                    + f"{job_label('Rounds:')} {info(str(job.rounds))}"
                )

            # Tiempos típicos por modo
            if job.mode.value in ("TABATA", "EMOM"):
                if job.work_time_in_seconds:
                    print(
                        "    "
                        + f"{job_label('Work:')} "
                        f"{info(str(job.work_time_in_seconds) + 's')}"
                    )
                if getattr(job, "rest_time_in_seconds", None) is not None:
                    print(
                        "    "
                        + f"{job_label('Rest (intervals):')} "
                        f"{info(str(job.rest_time_in_seconds) + 's')}"
                    )
            if job.mode.value in ("AMRAP", "EDT"):
                if job.work_time_in_minutes:
                    print(
                        "    "
                        + f"{job_label('Work:')} "
                        f"{info(str(job.work_time_in_minutes) + ' min')}"
                    )

            if job.mode.value == "FT":
                # FOR_TIME: no hay work_time fijo, pero Rounds suele estar
                pass

            print()
            input("    Press ENTER to start this job...")
            job_start_ts = time.time()
            input("    Press ENTER when you finish this job...")
            job_duration = int(time.time() - job_start_ts)
            print()
            print("    Job duration:", info(f"{job_duration}s"))
            job_note = input(prompt("Optional note for this job (ENTER to skip): ")).strip()

            job_record: Dict[str, Any] = {
                "index": j_idx,
                "name": job.name,
                "mode": job.mode.value,
                "duration_seconds": job_duration,
                "note": job_note or None,
            }
            stage_record["jobs"].append(job_record)

        # Fin de stage
        stage_duration = int(time.time() - stage_start_ts)
        print()
        print("  Stage duration:", info(f"{stage_duration}s"))
        stage_note = input("  Optional note for this stage (ENTER to skip): ").strip()
        stage_record["duration_seconds"] = stage_duration
        stage_record["note"] = stage_note or None

        run_record["stages"].append(stage_record)

    # ------------------------------------------------------------------
    # Fin de workout
    # ------------------------------------------------------------------
    total_duration = int(time.time() - workout_start_ts)
    print()
    print(success(f"Workout finished! Total time: {total_duration}s"))
    overall_note = input("Final overall note for this workout (ENTER to skip): ").strip()

    run_record["ended_at"] = _now_iso()
    run_record["duration_seconds"] = total_duration
    run_record["overall_note"] = overall_note or None

    # Guardar JSON
    target = _save_run_record(run_record)
    print()
    print(info(f"Run saved to {target}"))