# src/ui/cli/preview_v2.py
"""Formateo de workouts v2 para terminal.

Formateador ÚNICO que consumen tanto `preview` como el `run` (runner). Así
'ver' y 'ejecutar' un workout se ven exactamente igual.
"""
from __future__ import annotations

from typing import List

from src.domain_v2.workout_v2 import WorkoutV2
from src.i18n import t
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


def _tempo_labels():
    return (
        t("card.tempo_eccentric"),
        t("card.tempo_bottom"),
        t("card.tempo_concentric"),
        t("card.tempo_top"),
    )


def _format_tempo(raw) -> str:
    """'3-1-1-0' -> 'Eccentric 3s · Bottom pause 1s · ...'. 'X' = explosive.

    If the value isn't 4 phases, show it as-is (tolerant)."""
    parts = [p.strip() for p in str(raw).split("-") if p.strip()]
    if len(parts) != 4:
        return str(raw).strip()
    out = []
    for label, p in zip(_tempo_labels(), parts):
        if p.lower() == "x":
            out.append(t("card.tempo_explosive", label=label))
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
        return t("card.every_min", n=n // 60)
    return t("card.every_s", n=n)


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
    """Human-readable description of an intra-set technique."""
    typ = getattr(intra, "type", "")
    if typ == "drop_set":
        parts = []
        for d in getattr(intra, "drops", []) or []:
            reps = d.get("reps")
            w = d.get("weight")
            if isinstance(w, (int, float)):
                parts.append(f"{reps if reps is not None else '?'}×{w:g}kg")
            else:
                parts.append(f"{reps if reps is not None else '?'} reps")
        drop = t("card.intra_drop")
        return f"{drop}: " + " → ".join(parts) if parts else drop
    label = {"cluster": "cluster", "rest_pause": "rest-pause",
             "myo_reps": "myo-reps"}.get(typ, typ or "intra-set")
    scheme = "+".join(str(x) for x in (getattr(intra, "mini_sets", []) or []))
    rest = getattr(intra, "rest_seconds", None)
    rest_s = t("card.intra_rest_of", s=rest) if rest else ""
    return f"{label}: {scheme}{rest_s}" if scheme else f"{label}{rest_s}"


def format_job_card(job, index: int, total: int) -> List[str]:
    """Ficha legible de un job: cabecera + prescripción + ejercicios alineados.
    Devuelve líneas (el que llama decide cómo imprimirlas)."""
    lines: List[str] = []

    head = f"── Job {index}/{total} · {job.name}  "
    tag = f"[{job.mode.mode_label()}]"
    fill = max(3, BAR - len(head) - len(tag) - 1)
    lines.append(IND + job_title(head) + info(tag) + " " + job_title("─" * fill))
    if job.description:
        lines.append(IND + info(job.description))
    if getattr(job, "tags", None):
        lines.append(IND + info("🏷 " + ", ".join(job.tags)))
    def _row(label: str, value: str) -> str:
        # Etiqueta alineada a columna fija + valor, para una rejilla legible.
        return IND + job_label(label.ljust(10)) + info(value)

    meta: List[str] = []
    if job.rounds is not None:
        meta.append(_row(t("card.rounds"), str(job.rounds)))
    if job.cadence:
        meta.append(_row(t("card.cadence"), job.cadence))
    if getattr(job, "tempo", None):
        meta.append(_row(t("card.tempo"), _format_tempo(job.tempo)))
    if getattr(job, "interval_in_seconds", None):
        meta.append(_row(t("card.interval"), _fmt_interval(job.interval_in_seconds)))
    if getattr(job, "death_by", None) is not None:
        meta.append(_row(t("card.death_by"),
                         t("card.death_by_val", inc=job.death_by.increment_by)))

    tiempo = []
    if job.work_time_in_seconds is not None:
        tiempo.append(t("card.work_s", s=job.work_time_in_seconds))
    if job.work_time_in_minutes is not None:
        tiempo.append(t("card.window_min", m=job.work_time_in_minutes))
    if job.rest_time_in_seconds is not None:
        tiempo.append(t("card.rest_s", s=job.rest_time_in_seconds))
    if tiempo:
        meta.append(_row(t("card.time"), " · ".join(tiempo)))

    descanso = []
    if job.rest_between_exercises_in_seconds is not None:
        descanso.append(t("card.rest_between_ex", s=job.rest_between_exercises_in_seconds))
    if job.rest_between_rounds_in_seconds is not None:
        descanso.append(t("card.rest_between_rounds", s=job.rest_between_rounds_in_seconds))
    if descanso:
        meta.append(_row(t("card.rest"), " · ".join(descanso)))

    tecnica = []
    if job.eccentric_neg:
        tecnica.append(t("card.tech_eccentric"))
    if job.isometric_hold:
        tecnica.append(t("card.tech_isometric"))
    if tecnica:
        meta.append(_row(t("card.technique"), " · ".join(tecnica)))

    if meta:
        lines.append("")
        lines.extend(meta)

    exs = list(job.exercises or [])
    lines.append("")
    lines.append(IND + job_label(t("card.exercises")))
    if not exs:
        lines.append(IND + "  " + info(t("card.no_exercises")))
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
                    + info(t("card.set_n", i=s_idx))
                    + success(_prescription_str(st))
                )
        else:
            presc = _exercise_value(ex)
            row = f"{IND}  {i:>2}. " + info(name.ljust(width))
            if presc and presc != "—":
                row += "    " + success(presc)
            lines.append(row.rstrip())
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
    if getattr(workout, "tags", None):
        lines.append(info("🏷 " + ", ".join(workout.tags)))
    lines.append(info(t("card.n_stages", n=len(workout.stages))))
    lines.append("")
    for s_idx, stage in enumerate(workout.stages, start=1):
        lines.append(stage_title(t("card.stage_line", i=s_idx, name=stage.name, n=len(stage.jobs))))
        for job in stage.jobs:
            n = len(job.exercises or [])
            lines.append(
                "   " + job_label(f"· {job.name}")
                + info("   " + t("card.job_meta", mode=job.mode.mode_label(), n=n))
            )
        lines.append("")
    return "\n".join(lines)


def format_workout_v2_full(workout: WorkoutV2) -> str:
    """Detalle completo: cabecera + ficha de cada job por stage."""
    lines: List[str] = []
    lines.append(title(workout.name))
    if workout.description:
        lines.append(info(workout.description))
    if getattr(workout, "tags", None):
        lines.append(info("🏷 " + ", ".join(workout.tags)))
    lines.append(info(t("card.n_stages", n=len(workout.stages))))
    for s_idx, stage in enumerate(workout.stages, start=1):
        lines.append("")
        lines.append(stage_title(f"═══  Stage {s_idx}/{len(workout.stages)}: {stage.name}  ═══"))
        if stage.description:
            lines.append(stage_label(stage.description))
        if getattr(stage, "tags", None):
            lines.append(stage_label("🏷 " + ", ".join(stage.tags)))
        for j_idx, job in enumerate(stage.jobs, start=1):
            lines.append("")
            lines.extend(format_job_card(job, j_idx, len(stage.jobs)))
    return "\n".join(lines)
