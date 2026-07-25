# src/ui/cli/preview_v2.py
"""Formateo de workouts v2 para terminal.

Formateador ÚNICO que consumen tanto `preview` como el `run` (runner). Así
'ver' y 'ejecutar' un workout se ven exactamente igual.
"""
from __future__ import annotations

from typing import List

from src.domain_v2.workout_v2 import WorkoutV2
from src.ui.cli.style import (
    title,
    stage_title,
    job_title,
    job_label,
    stage_label,
    info,
    success,
)

IND = "   "     # sangría base de un job
BAR = 46        # ancho del separador de job


def _exercise_value(ex) -> str:
    """Prescripción de un ejercicio: distancia, reps y/o tiempo (+ peso)."""
    parts: List[str] = []
    if getattr(ex, "distance_in_meters", None) is not None:
        parts.append(f"{ex.distance_in_meters:g} m")
    if getattr(ex, "reps", None) is not None:
        parts.append(f"{ex.reps} reps")
    if getattr(ex, "work_time_in_seconds", None) is not None:
        parts.append(f"{ex.work_time_in_seconds} s")
    val = " · ".join(parts) if parts else "—"
    if getattr(ex, "weight", None) is not None:
        val += f"  @ {ex.weight:g} kg"
    return val


def format_job_card(job, index: int, total: int) -> List[str]:
    """Ficha legible de un job: cabecera + prescripción + ejercicios alineados.
    Devuelve líneas (el que llama decide cómo imprimirlas)."""
    lines: List[str] = []

    head = f"── Job {index}/{total} "
    lines.append(IND + job_title(head + "─" * max(0, BAR - len(head))))
    lines.append(IND + job_title(job.name) + "   " + info(f"[{job.mode.mode_label()}]"))
    if job.description:
        lines.append(IND + info(job.description))
    lines.append("")

    top = []
    if job.rounds is not None:
        top.append(job_label("Rondas: ") + info(str(job.rounds)))
    if job.cadence:
        top.append(job_label("Cadencia: ") + info(job.cadence))
    if top:
        lines.append(IND + "     ".join(top))

    tiempo = []
    if job.work_time_in_seconds is not None:
        tiempo.append(f"trabajo {job.work_time_in_seconds}s")
    if job.work_time_in_minutes is not None:
        tiempo.append(f"ventana {job.work_time_in_minutes} min")
    if job.rest_time_in_seconds is not None:
        tiempo.append(f"descanso {job.rest_time_in_seconds}s")
    if tiempo:
        lines.append(IND + job_label("Tiempo:   ") + info(" · ".join(tiempo)))

    descanso = []
    if job.rest_between_exercises_in_seconds is not None:
        descanso.append(f"{job.rest_between_exercises_in_seconds}s entre ejercicios")
    if job.rest_between_rounds_in_seconds is not None:
        descanso.append(f"{job.rest_between_rounds_in_seconds}s entre rondas")
    if descanso:
        lines.append(IND + job_label("Descanso: ") + info(" · ".join(descanso)))

    tecnica = []
    if job.eccentric_neg:
        tecnica.append("Excéntrico (NEG)")
    if job.isometric_hold:
        tecnica.append("Isométrico (HOLD)")
    if tecnica:
        lines.append(IND + job_label("Técnica:  ") + info(" · ".join(tecnica)))

    exs = list(job.exercises or [])
    lines.append("")
    lines.append(IND + job_label("Ejercicios"))
    if not exs:
        lines.append(IND + "  " + info("(sin ejercicios)"))
    width = min(max((len(e.name) for e in exs), default=0), 32)
    for i, ex in enumerate(exs, start=1):
        name = ex.name if len(ex.name) <= 32 else ex.name[:31] + "…"
        lines.append(f"{IND}  {i:>2}. " + info(name.ljust(width)) + "    " + success(_exercise_value(ex)))

    return lines


def format_workout_v2_summary(workout: WorkoutV2) -> str:
    """Resumen corto: cabecera + lista de jobs por stage (sin ejercicios)."""
    lines: List[str] = []
    lines.append(title(workout.name))
    if workout.description:
        lines.append(info(workout.description))
    lines.append(info(f"{len(workout.stages)} stages"))
    lines.append("")
    for s_idx, stage in enumerate(workout.stages, start=1):
        lines.append(stage_title(f"Stage {s_idx}: {stage.name}  ({len(stage.jobs)} jobs)"))
        for job in stage.jobs:
            n = len(job.exercises or [])
            lines.append(
                "   " + job_label(f"· {job.name}")
                + info(f"   [{job.mode.mode_label()}] · {n} ejercicios")
            )
        lines.append("")
    return "\n".join(lines)


def format_workout_v2_full(workout: WorkoutV2) -> str:
    """Detalle completo: cabecera + ficha de cada job por stage."""
    lines: List[str] = []
    lines.append(title(workout.name))
    if workout.description:
        lines.append(info(workout.description))
    lines.append(info(f"{len(workout.stages)} stages"))
    for s_idx, stage in enumerate(workout.stages, start=1):
        lines.append("")
        lines.append(stage_title(f"═══  Stage {s_idx}/{len(workout.stages)}: {stage.name}  ═══"))
        if stage.description:
            lines.append(stage_label(stage.description))
        for j_idx, job in enumerate(stage.jobs, start=1):
            lines.append("")
            lines.extend(format_job_card(job, j_idx, len(stage.jobs)))
    return "\n".join(lines)
