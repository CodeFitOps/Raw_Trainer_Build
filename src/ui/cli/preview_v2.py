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

_TEMPO_LABELS = ("Excéntrica", "Pausa abajo", "Concéntrica", "Pausa arriba")


def _format_tempo(raw) -> str:
    """'3-1-1-0' -> 'Excéntrica 3s · Pausa abajo 1s · Concéntrica 1s · Pausa arriba 0s'.

    Si el valor no son 4 fases, se muestra tal cual (tolerante). 'X' = explosiva.
    """
    parts = [p.strip() for p in str(raw).split("-") if p.strip()]
    if len(parts) != 4:
        return str(raw).strip()
    out = []
    for label, p in zip(_TEMPO_LABELS, parts):
        if p.lower() == "x":
            out.append(f"{label} explosiva")
        else:
            out.append(f"{label} {p}s")
    return " · ".join(out)


def _fmt_interval(n) -> str:
    """Duración de intervalo legible: 60 -> 'cada 1 min', 90 -> 'cada 90s'."""
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    if n >= 60 and n % 60 == 0:
        return f"cada {n // 60} min"
    return f"cada {n}s"


def _measure_str(obj) -> str:
    """Volumen de un ejercicio o serie: distancia, reps y/o tiempo."""
    parts: List[str] = []
    if getattr(obj, "distance_in_meters", None) is not None:
        parts.append(f"{obj.distance_in_meters:g} m")
    if getattr(obj, "reps", None) is not None:
        parts.append(f"{obj.reps} reps")
    if getattr(obj, "work_time_in_seconds", None) is not None:
        parts.append(f"{obj.work_time_in_seconds} s")
    return " · ".join(parts)


def _load_str(obj) -> str:
    """Carga de un ejercicio o serie: kg, %1RM y/o RPE."""
    parts: List[str] = []
    if getattr(obj, "weight", None) is not None:
        parts.append(f"{obj.weight:g} kg")
    if getattr(obj, "percent_1rm", None) is not None:
        parts.append(f"{obj.percent_1rm:g}% 1RM")
    if getattr(obj, "rpe", None) is not None:
        parts.append(f"RPE {obj.rpe:g}")
    return " · ".join(parts)


def _prescription_str(obj) -> str:
    """Prescripción compacta (volumen @ carga) de un ejercicio o serie."""
    measure = _measure_str(obj)
    load = _load_str(obj)
    if measure and load:
        return f"{measure}  @ {load}"
    if measure:
        return measure
    if load:
        return f"@ {load}"
    return "—"


def _exercise_value(ex) -> str:
    """Prescripción de un ejercicio sin series explícitas (compat)."""
    return _prescription_str(ex)


def _intra_set_line(intra) -> str:
    """Descripción legible de una técnica intra-serie."""
    t = getattr(intra, "type", "")
    if t == "drop_set":
        parts = []
        for d in getattr(intra, "drops", []) or []:
            reps = d.get("reps")
            w = d.get("weight")
            if isinstance(w, (int, float)):
                parts.append(f"{reps if reps is not None else '?'}×{w:g}kg")
            else:
                parts.append(f"{reps if reps is not None else '?'} reps")
        return "drop set: " + " → ".join(parts) if parts else "drop set"
    label = {"cluster": "cluster", "rest_pause": "rest-pause",
             "myo_reps": "myo-reps"}.get(t, t or "intra-serie")
    scheme = "+".join(str(x) for x in (getattr(intra, "mini_sets", []) or []))
    rest = getattr(intra, "rest_seconds", None)
    rest_s = f", descanso {rest}s" if rest else ""
    return f"{label}: {scheme}{rest_s}" if scheme else f"{label}{rest_s}"


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

    if getattr(job, "tempo", None):
        lines.append(IND + job_label("Tempo:    ") + info(_format_tempo(job.tempo)))

    if getattr(job, "interval_in_seconds", None):
        lines.append(IND + job_label("Intervalo: ") + info(_fmt_interval(job.interval_in_seconds)))

    if getattr(job, "death_by", None) is not None:
        lines.append(
            IND + job_label("Death By: ")
            + info(f"+{job.death_by.increment_by} rep por intervalo, hasta el fallo")
        )

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
        ex_sets = list(getattr(ex, "sets", None) or [])
        if ex_sets:
            # Prescripción por serie: cabecera (+ carga común) + una línea por serie.
            ex_load = _load_str(ex)
            header = info(name)
            if ex_load:
                header += "    " + success(f"@ {ex_load}")
            lines.append(f"{IND}  {i:>2}. " + header)
            for s_idx, st in enumerate(ex_sets, start=1):
                lines.append(
                    f"{IND}       "
                    + info(f"set {s_idx}: ")
                    + success(_prescription_str(st))
                )
        else:
            lines.append(
                f"{IND}  {i:>2}. "
                + info(name.ljust(width))
                + "    "
                + success(_exercise_value(ex))
            )
        intra = getattr(ex, "intra_set", None)
        if intra:
            lines.append(f"{IND}       " + info("↳ " + _intra_set_line(intra)))

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
