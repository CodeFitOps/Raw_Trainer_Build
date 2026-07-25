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


def build_segments(job: JobV2) -> Optional[List[Segment]]:
    """Secuencia de segmentos cronometrados para un job.

    Devuelve None si el modo del job aún no tiene executor driven (el llamador
    puede entonces caer al modo descriptivo).
    """
    if job.mode in (JobModeV2.INTERVAL, JobModeV2.TABATA):
        return _interval_segments(job)
    if job.mode is JobModeV2.AMRAP:
        return _amrap_segments(job)
    if job.mode is JobModeV2.FOR_TIME:
        return _for_time_segments(job)
    if job.mode is JobModeV2.EMOM:
        # Death-By necesita señal de fallo (captura de reps): de momento, descriptivo.
        if job.death_by is not None:
            return None
        return _emom_segments(job)
    return None
