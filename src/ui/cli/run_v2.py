# src/ui/cli/run_v2.py
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from src.domain_v2.workout_v2 import WorkoutV2
from src.infrastructure.workout_registry import _project_root
from src.i18n import t
from src.ui.cli.preview_v2 import format_job_card  # ficha compartida con `preview`
from src.ui.cli.style import (
    title,
    stage_title,
    stage_label,
    workout_label,
    prompt,
    info,
    success,
)

IND = "   "


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


def run_workout_v2_interactive(
    workout: WorkoutV2,
    *,
    source_path: Optional[Path] = None,
) -> None:
    """Runner interactivo (modo descriptivo: se muestra la ficha de cada job y
    se avanza manualmente con ENTER; se cronometra y se guarda la sesión)."""
    run_record = _build_run_record_base(workout, source_path)

    print()
    print(title(f"▶  {workout.name}"))
    if workout.description:
        print(info(workout.description))
    print(workout_label(t("run.stages_label")) + info(str(len(workout.stages))))
    print()
    input(prompt(t("run.enter_start")))

    workout_start_ts = time.time()

    for s_idx, stage in enumerate(workout.stages, start=1):
        print()
        print(stage_title(f"═══  Stage {s_idx}/{len(workout.stages)}: {stage.name}  ═══"))
        if stage.description:
            print(stage_label(stage.description))
        input(prompt(t("run.enter_stage")))

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
            for line in format_job_card(job, j_idx, len(stage.jobs)):
                print(line)
            print()

            input(IND + prompt(t("run.enter_job")))
            job_start_ts = time.time()
            input(IND + prompt(t("run.enter_done")))
            job_duration = int(time.time() - job_start_ts)
            print(IND + info(t("run.job_secs", d=job_duration)))
            job_note = input(IND + prompt(t("common.ask_note"))).strip()

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
        print(stage_label(t("run.stage_done", d=stage_duration)))
        stage_note = input(t("run.ask_stage_note")).strip()
        stage_record["duration_seconds"] = stage_duration
        stage_record["note"] = stage_note or None
        run_record["stages"].append(stage_record)

    total_duration = int(time.time() - workout_start_ts)
    print()
    print(success(t("run.workout_done", d=total_duration)))
    overall_note = input(t("run.ask_final_note")).strip()

    run_record["ended_at"] = _now_iso()
    run_record["duration_seconds"] = total_duration
    run_record["overall_note"] = overall_note or None

    target = _save_run_record(run_record)
    print(info(t("common.saved_session", name=target.name)))
