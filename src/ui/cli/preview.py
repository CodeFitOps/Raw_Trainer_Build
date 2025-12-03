# src/ui/cli/preview.py
from __future__ import annotations

from typing import List, Callable
import logging

from src.domain.workout_model import Workout
from src.ui.cli.style import (
    title,
    stage_title,
    job_title,
    workout_label,
    stage_label,
    job_label,
    info,
)

log = logging.getLogger(__name__)

LabelFn = Callable[[str], str]


def _indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line else line for line in text.splitlines())


def format_exercise_with_label(ex, label_fn: LabelFn) -> str:
    """
    Devuelve una línea tipo:
      - Bench Press: 10 reps @ 60 kg  (help: ...)
    donde:
      - El nombre del ejercicio (label) se pinta con label_fn (mismo color que el bloque).
      - El resto (reps, tiempo, peso, help) va en el color "info" (blanco/gris).
    """
    # Label: nombre del ejercicio con el mismo color que el bloque
    name_label = label_fn(f"- {ex.name}:")

    parts: List[str] = []

    # reps / tiempo como valores (info)
    if ex.reps is not None:
        parts.append(info(f"{ex.reps} reps"))
    if ex.work_time_in_seconds is not None:
        parts.append(info(f"{ex.work_time_in_seconds}s"))

    # peso
    if getattr(ex, "weight", None) is not None:
        parts.append(info(f"@ {ex.weight} kg"))

    # help
    if getattr(ex, "help", None):
        parts.append(info(f"(help: {ex.help})"))

    if parts:
        return " ".join([name_label] + parts)
    return name_label


def format_workout(workout: Workout) -> str:
    """
    Devuelve un string multi-línea con todos los detalles del workout:
    - Workout (nombre, descripción, nº stages)
    - Cada Stage (nombre, descripción, nº jobs)
    - Cada Job (nombre, modo, rondas, tiempos, rests, etc.)
    - Lista de ejercicios con reps, tiempos, peso, help...
    """
    lines: List[str] = []

    # Cabecera workout
    lines.append(title(f"Workout: {workout.name}"))

    # Description
    if workout.description:
        lines.append(
            f"{workout_label('Description:')} {info(workout.description)}"
        )
    else:
        lines.append(f"{workout_label('Description:')} {info('(none)')}")

    # Stages count
    lines.append(
        f"{workout_label('Stages:')} {info(str(len(workout.stages)))}"
    )
    lines.append("")  # línea en blanco

    # Stages
    for s_idx, stage in enumerate(workout.stages, start=1):
        # Cabecera stage
        lines.append(stage_title(f"Stage {s_idx}: {stage.name}"))

        # Stage description
        if stage.description:
            lines.append(
                "  "
                + f"{stage_label('Description:')} {info(stage.description)}"
            )
        else:
            lines.append(
                "  " + f"{stage_label('Description:')} {info('(none)')}"
            )

        # Jobs count
        lines.append(
            "  "
            + f"{stage_label('Jobs:')} {info(str(len(stage.jobs)))}"
        )
        lines.append("")

        # Jobs
        for j_idx, job in enumerate(stage.jobs, start=1):
            mode_str = job.mode.value
            header = job_title(f"  Job {j_idx}: {job.name} [mode={mode_str}]")
            lines.append(header)

            # Descripción del job
            if job.description:
                lines.append(
                    "    "
                    + f"{job_label('Desc:')} {info(job.description)}"
                )

            # Modo genérico: rondas
            if job.rounds is not None:
                lines.append(
                    "    "
                    + f"{job_label('Rounds:')} {info(str(job.rounds))}"
                )

            # Campos de tiempo/descanso comunes
            if job.work_time_in_seconds is not None:
                lines.append(
                    "    "
                    + f"{job_label('Work time (job-level):')} "
                    f"{info(str(job.work_time_in_seconds) + 's')}"
                )
            if job.work_time_in_minutes is not None:
                lines.append(
                    "    "
                    + f"{job_label('Work time (job-level):')} "
                    f"{info(str(job.work_time_in_minutes) + ' min')}"
                )
            if job.rest_time_in_seconds is not None:
                lines.append(
                    "    "
                    + f"{job_label('Rest time (between intervals):')} "
                    f"{info(str(job.rest_time_in_seconds) + 's')}"
                )
            if job.rest_between_exercises_in_seconds is not None:
                lines.append(
                    "    "
                    + f"{job_label('Rest between exercises:')} "
                    f"{info(str(job.rest_between_exercises_in_seconds) + 's')}"
                )
            if job.rest_between_rounds_in_seconds is not None:
                lines.append(
                    "    "
                    + f"{job_label('Rest between rounds:')} "
                    f"{info(str(job.rest_between_rounds_in_seconds) + 's')}"
                )

            # Otros metadatos
            if job.cadence:
                lines.append(
                    "    "
                    + f"{job_label('Cadence:')} {info(job.cadence)}"
                )
            if job.eccentric_neg is not None:
                lines.append(
                    "    "
                    + f"{job_label('Eccentric (NEG):')} "
                    f"{info(str(job.eccentric_neg))}"
                )
            if job.isometric_hold is not None:
                lines.append(
                    "    "
                    + f"{job_label('Isometric (HOLD):')} "
                    f"{info(str(job.isometric_hold))}"
                )

            # Ejercicios
            lines.append("    " + f"{job_label('Exercises:')}")
            if not job.exercises:
                lines.append("      " + info("(none)"))
            else:
                for ex in job.exercises:
                    lines.append(
                        "      " + format_exercise_with_label(ex, job_label)
                    )

            lines.append("")  # separación entre jobs

        lines.append("")  # separación entre stages

    return "\n".join(lines)