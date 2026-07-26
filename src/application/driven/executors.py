# src/application/driven/executors.py
"""Executors driven: de un JobV2 a una secuencia de segmentos cronometrados.

Cada MODE que soporte el modo driven aporta aquí su forma de construir la
secuencia. La LÓGICA de ejecución vive en estos executors (no se duplica en
la UI): el player solo reproduce lo que devuelven.

Relojes soportados:
  - interval / tabata : work/rest xN (ejercicios rotan por ronda).
  - amrap             : una ventana con cuenta atrás; se repite el circuito.
  - for_time          : cronómetro ascendente (lo para el usuario al terminar).
  - emom              : un intervalo con cuenta atrás por ronda.

Pendiente (necesita captura de reps en driven): EMOM Death-By (señal de fallo),
edt (densidad), custom_sets guiado.
"""
from __future__ import annotations

from typing import List, Optional

from src.domain_v2.workout_v2 import JobV2, JobModeV2
from src.application.driven.segments import Segment

# Cuenta atrás de preparación antes del primer tramo.
PREPARE_SECONDS = 10


def _exercise_line(ex) -> str:
    """Descripción compacta de un ejercicio para checklists (circuito/movimientos)."""
    if getattr(ex, "sets", None):
        reps = "-".join(str(s.reps) for s in ex.sets if s.reps is not None)
        base = f"{ex.name} {reps}" if reps else ex.name
    elif ex.reps is not None:
        base = f"{ex.name} x{ex.reps}"
    elif ex.work_time_in_seconds is not None:
        base = f"{ex.name} {ex.work_time_in_seconds}s"
    elif ex.distance_in_meters is not None:
        base = f"{ex.name} {ex.distance_in_meters:g} m"
    else:
        base = ex.name
    if ex.weight is not None:
        base += f" @{ex.weight:g}kg"
    return base


def _prepare() -> Segment:
    # label vacío: el player ya rotula "PREPÁRATE" según el kind.
    return Segment(kind="prepare", duration_seconds=PREPARE_SECONDS, label="")


def _interval_segments(job: JobV2) -> List[Segment]:
    """interval / tabata: work/rest repetido N rondas.

    Los ejercicios rotan por ronda (ronda k -> ejercicio[(k-1) % nº ejercicios]).
    No se añade descanso tras la última ronda (el bloque termina en trabajo).
    """
    rounds = job.rounds or 0
    work = job.work_time_in_seconds or 0
    rest = job.rest_time_in_seconds or 0
    exercises = [e.name for e in (job.exercises or [])] or ["Trabajo"]

    segments: List[Segment] = []
    if rounds <= 0 or work <= 0:
        return segments

    if PREPARE_SECONDS > 0:
        segments.append(_prepare())

    for k in range(1, rounds + 1):
        ex = exercises[(k - 1) % len(exercises)]
        segments.append(
            Segment(
                kind="work",
                duration_seconds=work,
                label=ex,
                exercise=ex,
                round_index=k,
                total_rounds=rounds,
            )
        )
        if rest > 0 and k < rounds:
            segments.append(
                Segment(
                    kind="rest",
                    duration_seconds=rest,
                    label="Descanso",
                    round_index=k,
                    total_rounds=rounds,
                )
            )

    return segments


def _amrap_segments(job: JobV2) -> List[Segment]:
    """amrap: una única ventana con cuenta atrás; el circuito se repite AMRAP."""
    secs = job.work_time_in_seconds or ((job.work_time_in_minutes or 0) * 60)
    if secs <= 0:
        return []
    items = [_exercise_line(e) for e in (job.exercises or [])]
    segments: List[Segment] = []
    if PREPARE_SECONDS > 0:
        segments.append(_prepare())
    segments.append(
        Segment(
            kind="window",
            duration_seconds=secs,
            label="todas las rondas posibles",
            items=items,
        )
    )
    return segments


def _for_time_segments(job: JobV2) -> List[Segment]:
    """for_time: cronómetro ascendente; el usuario lo para al terminar el trabajo."""
    items = [_exercise_line(e) for e in (job.exercises or [])]
    rounds = job.rounds or 1
    label = "completa lo antes posible"
    if rounds > 1:
        label = f"{rounds} rondas — lo antes posible"
    segments: List[Segment] = []
    if PREPARE_SECONDS > 0:
        segments.append(_prepare())
    segments.append(
        Segment(kind="stopwatch", duration_seconds=0, label=label, items=items)
    )
    return segments


def _emom_segments(job: JobV2) -> List[Segment]:
    """emom: un intervalo con cuenta atrás por ronda; ejercicios rotan por ronda."""
    interval = job.interval_in_seconds or job.work_time_in_seconds or 60
    rounds = job.rounds or 0
    exercises = list(job.exercises or [])
    if rounds <= 0 or interval <= 0 or not exercises:
        return []
    segments: List[Segment] = []
    if PREPARE_SECONDS > 0:
        segments.append(_prepare())
    for k in range(1, rounds + 1):
        ex = exercises[(k - 1) % len(exercises)]
        segments.append(
            Segment(
                kind="work",
                duration_seconds=interval,
                label=_exercise_line(ex),
                exercise=ex.name,
                round_index=k,
                total_rounds=rounds,
                items=["haz las reps y descansa el resto del intervalo"],
            )
        )
    return segments


def _edt_segments(job: JobV2) -> List[Segment]:
    """edt: una ventana de densidad; acumula el máximo de reps en el tiempo dado."""
    secs = job.work_time_in_seconds or ((job.work_time_in_minutes or 0) * 60)
    if secs <= 0:
        return []
    items = [_exercise_line(e) for e in (job.exercises or [])]
    segments: List[Segment] = []
    if PREPARE_SECONDS > 0:
        segments.append(_prepare())
    segments.append(
        Segment(
            kind="density",
            duration_seconds=secs,
            label="acumula el máximo de reps",
            items=items,
        )
    )
    return segments


def _prescr(obj) -> str:
    """Prescripción compacta de un ejercicio o serie: volumen @ carga."""
    parts = []
    d = getattr(obj, "distance_in_meters", None)
    if d is not None:
        parts.append(f"{d:g} m")
    rp = getattr(obj, "reps", None)
    if rp is not None:
        parts.append(f"{rp} reps")
    wt = getattr(obj, "work_time_in_seconds", None)
    if wt is not None:
        parts.append(f"{wt}s")
    load = []
    w = getattr(obj, "weight", None)
    if w is not None:
        load.append(f"{w:g}kg")
    pc = getattr(obj, "percent_1rm", None)
    if pc is not None:
        load.append(f"{pc:g}%1RM")
    rpe = getattr(obj, "rpe", None)
    if rpe is not None:
        load.append(f"RPE{rpe:g}")
    body = " · ".join(parts)
    if load:
        body = (body + "  @ " + " · ".join(load)) if body else "@ " + " · ".join(load)
    return body or "—"


def _round_of(ex, r):
    """Prescripción para la ronda r: la serie r-ésima si el ejercicio define
    `sets`, si no el propio ejercicio (misma prescripción cada ronda)."""
    sets = getattr(ex, "sets", None) or []
    if sets and r <= len(sets):
        return sets[r - 1]
    return ex


def _intra_set_segments(ex, r: int, rounds: int) -> List[Segment]:
    """Expande una serie con técnica intra-serie en mini-esfuerzos (+ descanso intra)."""
    intra = ex.intra_set
    segs: List[Segment] = []
    if intra.type == "drop_set":
        drops = intra.drops or []
        for i, d in enumerate(drops):
            reps = d.get("reps")
            w = d.get("weight")
            if isinstance(w, (int, float)):
                item = f"{reps if reps is not None else '?'} reps @ {w:g}kg"
            else:
                item = f"{reps if reps is not None else '?'} reps"
            segs.append(Segment(kind="set", duration_seconds=0,
                                label=f"{ex.name} (drop {i + 1}/{len(drops)})",
                                round_index=r, total_rounds=rounds, items=[item]))
        return segs
    # cluster / rest_pause / myo_reps: mini-esfuerzos con descanso intra
    mini = intra.mini_sets or ([ex.reps] if ex.reps else [])
    rest = intra.rest_seconds or 0
    tag = {"cluster": "cluster", "rest_pause": "rest-pause",
           "myo_reps": "myo-reps"}.get(intra.type, intra.type or "intra")
    for i, reps in enumerate(mini):
        item = f"{reps} reps"
        if ex.weight is not None:
            item += f"  @ {ex.weight:g}kg"
        segs.append(Segment(kind="set", duration_seconds=0,
                            label=f"{ex.name} · {tag} {i + 1}/{len(mini)}",
                            round_index=r, total_rounds=rounds, items=[item]))
        if rest > 0 and i < len(mini) - 1:
            segs.append(Segment(kind="rest", duration_seconds=rest,
                                label="Descanso intra-serie"))
    return segs


def _custom_sets_segments(job: JobV2) -> List[Segment]:
    """custom_sets guiado: cada serie a tu ritmo (ENTER) o cronometrada (holds),
    con descansos entre ejercicios y entre rondas."""
    rounds = job.rounds or 1
    exs = list(job.exercises or [])
    if not exs:
        return []
    rest_ex = job.rest_between_exercises_in_seconds or 0
    rest_rd = job.rest_between_rounds_in_seconds or 0
    segs: List[Segment] = []
    if PREPARE_SECONDS > 0:
        segs.append(_prepare())
    for r in range(1, rounds + 1):
        for ei, ex in enumerate(exs):
            if getattr(ex, "intra_set", None):
                segs.extend(_intra_set_segments(ex, r, rounds))
            else:
                target = _round_of(ex, r)
                pres = _prescr(target)
                wt = getattr(target, "work_time_in_seconds", None)
                if wt:
                    segs.append(Segment(kind="work", duration_seconds=wt, label=ex.name,
                                        round_index=r, total_rounds=rounds, items=[pres]))
                else:
                    segs.append(Segment(kind="set", duration_seconds=0, label=ex.name,
                                        round_index=r, total_rounds=rounds, items=[pres]))
            if rest_ex > 0 and ei < len(exs) - 1:
                segs.append(Segment(kind="rest", duration_seconds=rest_ex, label="Descanso"))
        if rest_rd > 0 and r < rounds:
            segs.append(Segment(kind="rest", duration_seconds=rest_rd,
                                label="Descanso entre rondas"))
    return segs


def _carry_segments(job: JobV2) -> List[Segment]:
    """carry/hold guiado: holds cronometrados (work_time) y acarreos a tu ritmo
    (distancia/reps), con descanso entre rondas."""
    rounds = job.rounds or 1
    exs = list(job.exercises or [])
    if not exs:
        return []
    rest_rd = job.rest_between_rounds_in_seconds or job.rest_time_in_seconds or 0
    segs: List[Segment] = []
    if PREPARE_SECONDS > 0:
        segs.append(_prepare())
    for r in range(1, rounds + 1):
        for ex in exs:
            pres = _prescr(ex)
            wt = getattr(ex, "work_time_in_seconds", None)
            if wt:
                segs.append(Segment(kind="work", duration_seconds=wt, label=ex.name,
                                    round_index=r, total_rounds=rounds, items=[pres]))
            else:
                segs.append(Segment(kind="set", duration_seconds=0, label=ex.name,
                                    round_index=r, total_rounds=rounds, items=[pres]))
        if rest_rd > 0 and r < rounds:
            segs.append(Segment(kind="rest", duration_seconds=rest_rd,
                                label="Descanso entre rondas"))
    return segs


def _ladder_segments(job: JobV2) -> List[Segment]:
    """ladder guiado: una serie por peldaño, con las reps subiendo o bajando."""
    extra = getattr(job, "extra", {}) or {}
    total = extra.get("total_rounds") or job.rounds or 0
    ladder_type = str(extra.get("ladder_type") or "ASCENDING").upper()
    inc = extra.get("increment_by")
    if not isinstance(inc, int) or inc == 0:
        inc = 1
    exs = list(job.exercises or [])
    if total <= 0 or not exs:
        return []
    segs: List[Segment] = []
    if PREPARE_SECONDS > 0:
        segs.append(_prepare())
    for k in range(1, total + 1):
        for ex in exs:
            start = ex.reps if ex.reps else 1
            if ladder_type == "DESCENDING":
                reps = max(1, start - (k - 1) * inc)
            else:
                reps = start + (k - 1) * inc
            item = f"{reps} reps"
            if ex.weight is not None:
                item += f"  @ {ex.weight:g}kg"
            segs.append(Segment(kind="set", duration_seconds=0, label=ex.name,
                                round_index=k, total_rounds=total, items=[item]))
    return segs


def build_segments(job: JobV2) -> Optional[List[Segment]]:
    """Secuencia de segmentos cronometrados para un job.

    Devuelve None si el modo del job aún no tiene executor driven (el llamador
    puede entonces caer al modo descriptivo). Death-By (emom) también devuelve
    None: lo conduce un flujo dedicado en el player (intervalos hasta el fallo).
    """
    if job.mode in (JobModeV2.INTERVAL, JobModeV2.TABATA):
        return _interval_segments(job)
    if job.mode is JobModeV2.AMRAP:
        return _amrap_segments(job)
    if job.mode is JobModeV2.FOR_TIME:
        return _for_time_segments(job)
    if job.mode is JobModeV2.EMOM:
        if job.death_by is not None:
            return None  # lo maneja _drive_death_by en el player
        return _emom_segments(job)
    if job.mode is JobModeV2.EDT:
        return _edt_segments(job)
    if job.mode is JobModeV2.CUSTOM_SETS:
        return _custom_sets_segments(job)
    if job.mode is JobModeV2.CARRY:
        return _carry_segments(job)
    if job.mode is JobModeV2.LADDER:
        return _ladder_segments(job)
    return None
