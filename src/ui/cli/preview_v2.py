# src/ui/cli/preview_v2.py
from __future__ import annotations

from typing import List

from src.domain_v2.workout_v2 import WorkoutV2, StageV2, JobV2, ExerciseV2
from src.ui.cli.style import (
    title,
    stage_title,
    stage_label,
    job_title,
    job_label,
    workout_label,
    info,
)


def format_workout_v2(workout: WorkoutV2) -> str:
    """
    Pretty print para el modelo v2:
    - Cabecera de workout
    - Stages
    - Jobs
    - Ejercicios

    Usa JobModeV2.mode_label() y JobModeV2.mode_description() para mostrar
    información fija del tipo de trabajo (MODE) + la descripción del job.
    """
    lines: List[str] = []

    # Cabecera workout
    lines.append(title(f"Workout: {workout.name}"))

    if workout.description:
        lines.append(
            f"{workout_label('Description:')} {info(workout.description)}"
        )
    else:
        lines.append(
            f"{workout_label('Description:')} {info('(none)')}"
        )

    lines.append(
        f"{workout_label('Stages:')} {info(str(len(workout.stages)))}"
    )
    lines.append("")  # línea en blanco

    # Stages
    for s_idx, stage in enumerate(workout.stages, start=1):
        lines.extend(_format_stage_v2(stage, index=s_idx))
        lines.append("")  # separación entre stages

    return "\n".join(lines)


def _format_stage_v2(stage: StageV2, index: int) -> List[str]:
    lines: List[str] = []

    # Cabecera stage
    lines.append(stage_title(f"Stage {index}: {stage.name}"))

    if stage.description:
        lines.append(
            "  "
            + f"{stage_label('Description:')} {info(stage.description)}"
        )
    else:
        lines.append(
            "  "
            + f"{stage_label('Description:')} {info('(none)')}"
        )

    lines.append(
        "  "
        + f"{stage_label('Jobs:')} {info(str(len(stage.jobs)))}"
    )
    lines.append("")  # línea en blanco

    # Jobs
    for j_idx, job in enumerate(stage.jobs, start=1):
        lines.extend(_format_job_v2(job, index=j_idx))
        lines.append("")  # separación entre jobs

    return lines


def _format_job_v2(job: JobV2, index: int) -> List[str]:
    """
    Bloque de impresión para un JobV2:
    - Nombre + modo
    - Descripción fija del MODE (mode_description)
    - Descripción del job
    - Campos clave (rounds, work, rests, cadence, NEG, HOLD)
    - Ejercicios
    """
    lines: List[str] = []

    # Cabecera con etiqueta corta del modo
    header = job_title(
        f"  Job {index}: {job.name} [mode={job.mode.mode_label()}]"
    )
    lines.append(header)

    # Descripción fija del tipo de trabajo (MODE)
    mode_desc = job.mode.mode_description()
    if mode_desc:
        lines.append(
            "    " + job_label("Mode:") + f" {info(mode_desc)}"
        )

    # Descripción específica del job
    if job.description:
        lines.append(
            "    " + job_label("Desc:") + f" {info(job.description)}"
        )

    # Rounds
    if job.rounds is not None:
        lines.append(
            "    " + job_label("Rounds:") + f" {info(str(job.rounds))}"
        )

    # Work times
    if job.work_time_in_seconds is not None:
        lines.append(
            "    "
            + job_label("Work:")
            + f" {info(str(job.work_time_in_seconds) + 's')}"
        )
    if job.work_time_in_minutes is not None:
        lines.append(
            "    "
            + job_label("Work:")
            + f" {info(str(job.work_time_in_minutes) + ' min')}"
        )

    # Rests
    if job.rest_time_in_seconds is not None:
        lines.append(
            "    "
            + job_label("Rest (intervals):")
            + f" {info(str(job.rest_time_in_seconds) + 's')}"
        )
    if job.rest_between_exercises_in_seconds is not None:
        lines.append(
            "    "
            + job_label("Rest between exercises:")
            + f" {info(str(job.rest_between_exercises_in_seconds) + 's')}"
        )
    if job.rest_between_rounds_in_seconds is not None:
        lines.append(
            "    "
            + job_label("Rest between rounds:")
            + f" {info(str(job.rest_between_rounds_in_seconds) + 's')}"
        )

    # Cadencia / flags
    if job.cadence:
        lines.append(
            "    " + job_label("Cadence:") + f" {info(job.cadence)}"
        )

    if job.eccentric_neg:
        lines.append(
            "    " + job_label("Eccentric (NEG):") + f" {info('True')}"
        )
    if job.isometric_hold:
        lines.append(
            "    " + job_label("Isometric (HOLD):") + f" {info('True')}"
        )

    # Ejercicios
    lines.append("    " + job_label("Exercises:"))
    if not job.exercises:
        lines.append("      " + info("(none)"))
    else:
        for ex in job.exercises:
            lines.append("      " + _format_exercise_v2(ex))

    return lines


def _format_exercise_v2(ex: ExerciseV2) -> str:
    """
    Línea simple tipo:
      - Bench Press: 10 reps @ 60.0 kg
      - Hollow Hold: 30s
    """
    parts: List[str] = []

    if ex.reps is not None:
        parts.append(f"{ex.reps} reps")
    if getattr(ex, "work_time_in_seconds", None) is not None:
        parts.append(f"{ex.work_time_in_seconds}s")
    if ex.weight is not None:
        parts.append(f"@ {ex.weight} kg")

    if parts:
        return f"- {ex.name}: " + " ".join(parts)
    return f"- {ex.name}"