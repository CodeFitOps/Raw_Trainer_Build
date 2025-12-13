# src/ui/cli/preview_v2.py
from __future__ import annotations

from typing import List

from src.ui.cli.style import (
    title,
    stage_title,
    job_label,
    info,
    stage_label,
    prompt,
    job_title,

)
from src.domain_v2.workout_v2 import WorkoutV2

# Si tienes un helper para formatear ejercicios en v2, úsalo.
# Si no existe, usamos uno interno sencillo.
def _fmt_exercise_line(ex) -> str:
    # ExerciseV2 suele tener name, reps, work_time_in_seconds, weight
    name = getattr(ex, "name", "?")
    reps = getattr(ex, "reps", None)
    wts = getattr(ex, "work_time_in_seconds", None)
    weight = getattr(ex, "weight", None)

    parts: List[str] = []
    if reps is not None:
        parts.append(f"{reps} reps")
    if wts is not None:
        parts.append(f"{wts}s")
    if weight is not None:
        parts.append(f"@ {float(weight):.1f} kg")

    if parts:
        return f"      - {name}: " + " ".join(parts)
    return f"      - {name}"


# ---------------------------------------------------------------------
# PUBLIC API (lo que importa main_cli)
# ---------------------------------------------------------------------

# ---------------------------------------------------------------------
# PUBLIC API (usado por main_cli)
# ---------------------------------------------------------------------

def format_workout_v2(workout: WorkoutV2) -> str:
    """
    Preview v2 SHORT SUMMARY.
    No imprime detalles completos, solo estructura.
    """
    return format_workout_v2_summary(workout)


# ---------------------------------------------------------------------
# SHORT SUMMARY FORMATTER
# ---------------------------------------------------------------------

def format_workout_v2_summary(workout: WorkoutV2) -> str:
    lines: List[str] = []

    lines.append(title(f"Workout: {workout.name}"))
    if workout.description:
        lines.append(info(f"Description: {workout.description}"))
    lines.append(info(f"Stages: {len(workout.stages)}"))
    lines.append("")

    for s_idx, stage in enumerate(workout.stages, start=1):
        lines.append(
            stage_title(f"Stage {s_idx}: {stage.name} ({len(stage.jobs)} jobs)")
        )

        for job in stage.jobs:
            mode = job.mode.value if hasattr(job.mode, "value") else str(job.mode)
            lines.append(
                job_label(f"  - {job.name} [{mode}]")
            )

        lines.append("")

    return "\n".join(lines)

# -----------------------------
# FULL DETAILS (paginated)
# -----------------------------
def format_workout_v2_full(workout: WorkoutV2) -> str:
    """
    Full pretty print (si ya lo tienes en otra parte, puedes delegar).
    Aquí hacemos un full “clásico” con style (no blanco).
    """
    lines: List[str] = []
    lines.append(title(f"\nWorkout: {workout.name}"))
    if workout.description:
        lines.append(info(f"Description: {workout.description}"))
    lines.append(info(f"Stages: {len(workout.stages)}"))
    lines.append("")

    for s_idx, stage in enumerate(workout.stages, start=1):
        lines.extend(_format_stage_full(stage, index=s_idx))
        lines.append("")

    return "\n".join(lines)


def _format_stage_full(stage: StageV2, index: int) -> List[str]:
    lines: List[str] = []
    lines.append(stage_title(f"Stage {index}: {stage.name}"))
    if stage.description:
        lines.append(stage_label(f"  Description: {stage.description}"))
    lines.append(stage_label(f"  Jobs: {len(stage.jobs)}"))
    lines.append("")

    for j_idx, job in enumerate(stage.jobs, start=1):
        lines.extend(_format_job_full(job, index=j_idx))
        lines.append("")

    return lines


def _format_job_full(job: JobV2, index: int) -> List[str]:
    lines: List[str] = []
    mode = str(getattr(job, "mode", ""))

    lines.append(job_title(f"  Job {index}: {job.name} [mode={mode}]"))

    # “Mode description” si lo has añadido en v2 (opcional)
    mode_desc = getattr(job, "mode_description", None)
    if isinstance(mode_desc, str) and mode_desc.strip():
        lines.append(job_label(f"    Mode: {mode_desc.strip()}"))

    desc = getattr(job, "description", None)
    if isinstance(desc, str) and desc.strip():
        lines.append(job_label(f"    Desc: {desc.strip()}"))

    # Campos típicos en v2 (si existen)
    rounds = getattr(job, "rounds", None)
    if rounds is not None:
        lines.append(job_label(f"    Rounds: {rounds}"))

    wts = getattr(job, "work_time_in_seconds", None)
    if wts is not None:
        lines.append(job_label(f"    Work: {wts}s"))

    wtm = getattr(job, "work_time_in_minutes", None)
    if wtm is not None:
        lines.append(job_label(f"    Work: {wtm} min"))

    cadence = getattr(job, "cadence", None)
    if cadence:
        lines.append(job_label(f"    Cadence: {cadence}"))

    # flags
    if getattr(job, "eccentric_neg", False):
        lines.append(job_label("    Eccentric (NEG): True"))
    if getattr(job, "isometric_hold", False):
        lines.append(job_label("    Isometric (HOLD): True"))

    # rests
    rbe = getattr(job, "rest_between_exercises_in_seconds", None)
    if rbe is not None:
        lines.append(job_label(f"    Rest between exercises: {rbe}s"))

    rbr = getattr(job, "rest_between_rounds_in_seconds", None)
    if rbr is not None:
        lines.append(job_label(f"    Rest between rounds: {rbr}s"))

    rti = getattr(job, "rest_time_in_seconds", None)
    if rti is not None:
        lines.append(job_label(f"    Rest (intervals): {rti}s"))

    # exercises
    lines.append(job_label("    Exercises:"))
    for ex in getattr(job, "exercises", []) or []:
        lines.append(_fmt_exercise_line(ex))

    return lines


def print_full_details_paginated(workout: WorkoutV2) -> None:
    """
    No “dump”: imprime stage/job y espera ENTER para seguir.
    Sin prompts de start/finish (esto NO es el runner).
    """
    print(format_workout_v2_full_header(workout))

    for s_idx, stage in enumerate(workout.stages, start=1):
        print("")
        print(stage_title(f"Stage {s_idx}: {stage.name}"))
        if stage.description:
            print(stage_label(f"  Description: {stage.description}"))
        input(prompt("\n  Press ENTER to show jobs..."))

        for j_idx, job in enumerate(stage.jobs, start=1):
            print("")
            for line in _format_job_full(job, index=j_idx):
                print(line)
            input(prompt("\n  Press ENTER for next job..."))

        input(prompt("\nPress ENTER for next stage..."))


def format_workout_v2_full_header(workout: WorkoutV2) -> str:
    lines: List[str] = []
    lines.append(title(f"\nWorkout: {workout.name}"))
    if workout.description:
        lines.append(info(f"Description: {workout.description}"))
    lines.append(info(f"Stages: {len(workout.stages)}"))
    return "\n".join(lines)