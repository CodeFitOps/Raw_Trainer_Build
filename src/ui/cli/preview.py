# src/ui/cli/preview.py
from __future__ import annotations

from typing import List, Callable
import logging

from src.domain.workout_model import Workout, Exercise
from src.ui.cli.style import (
    title,
    stage_title,
    stage_label,
    job_title,
    job_label,
    workout_label,
    info,
    success,
)

log = logging.getLogger(__name__)

LabelFn = Callable[[str], str]


def _indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line else line for line in text.splitlines())


def format_exercise_with_label(ex: Exercise, job_label: LabelFn) -> str:
    """
    Devuelve un bloque de texto formateado para un Exercise.

    Ejemplos de salida:

      - Jumping Jacks: 20 reps
      - Hollow Hold: 30s
      - Front Squat: 5 reps @ 80.0 kg

    Para EDT:
      - No mostramos reps (aunque internamente se haya forzado a 1).
      - No mostramos el flag interno _edt_no_reps en Extra.
    """
    lines: list[str] = []

    # Flag interno EDT: viene de Job.from_dict (se guarda en ex.extra["_edt_no_reps"])
    edt_flag = False
    if isinstance(ex.extra, dict):
        edt_flag = bool(ex.extra.get("_edt_no_reps"))

    # Línea principal: nombre + reps + tiempo + peso
    details: list[str] = []

    # En EDT no mostramos reps, aunque internamente haya reps=1
    if ex.reps is not None and not edt_flag:
        details.append(f"{ex.reps} reps")

    if getattr(ex, "work_time_in_seconds", None) is not None:
        details.append(f"{ex.work_time_in_seconds}s")

    if ex.weight is not None:
        details.append(f"@ {ex.weight} kg")

    if details:
        main = f"- {ex.name}: " + " ".join(details)
    else:
        main = f"- {ex.name}"

    lines.append(main)

    # Notes / descripción opcional
    if ex.notes:
        lines.append("    " + job_label("Notes:") + f" {ex.notes}")

    # Extra fields (cualquier cosa que venga del YAML y no sea core)
    # Ocultamos el flag interno _edt_no_reps para no ensuciar la salida
    extras_filtered = {}
    if isinstance(ex.extra, dict):
        extras_filtered = {
            k: v for k, v in ex.extra.items() if k != "_edt_no_reps"
        }

    if extras_filtered:
        lines.append("    " + job_label("Extra:"))
        for k, v in sorted(extras_filtered.items()):
            lines.append(f"      {k}: {v}")

    return "\n".join(lines)


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
            # Internal mode description (our own, not user-provided)
            try:
                mode_info = job.mode.mode_description
            except AttributeError:
                mode_info = None

            if mode_info:
                lines.append(
                    "    "
                    + f"{job_label('Mode info:')} {info(mode_info)}"
                )

            # Descripción del job
            if job.description:
                lines.append(
                    "    "
                    + f"{job_label('Desc:')} {info(job.description)}"
                )

            # Rounds
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

            # Solo mostramos NEG / HOLD si están activos (True)
            if job.eccentric_neg:
                lines.append(
                    "    "
                    + f"{job_label('Eccentric (NEG):')} "
                    f"{info('True')}"
                )
            if job.isometric_hold:
                lines.append(
                    "    "
                    + f"{job_label('Isometric (HOLD):')} "
                    f"{info('True')}"
                )

            # Ejercicios
            lines.append("    " + f"{job_label('Exercises:')}")
            if not job.exercises:
                lines.append("      " + info("(none)"))
            else:
                for ex in job.exercises:
                    # Cada ejercicio se indenta dentro de la lista
                    formatted = format_exercise_with_label(ex, job_label)
                    # Aseguramos indentado de 6 espacios para el bloque entero
                    lines.append(_indent(formatted, 6))

            lines.append("")  # separación entre jobs

        lines.append("")  # separación entre stages

    return "\n".join(lines)