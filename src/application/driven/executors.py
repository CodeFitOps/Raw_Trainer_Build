# src/application/driven/executors.py
"""Executors driven: de un JobV2 a una secuencia de segmentos cronometrados.

Cada MODE que soporte el modo driven aporta aquí su forma de construir la
secuencia. La LÓGICA de ejecución vive en estos executors (no se duplica en
la UI): el player solo reproduce lo que devuelven.

Corte vertical inicial: interval / tabata (misma ejecución: work/rest xN).
"""
from __future__ import annotations

from typing import List, Optional

from src.domain_v2.workout_v2 import JobV2, JobModeV2
from src.application.driven.segments import Segment

# Cuenta atrás de preparación antes del primer tramo de trabajo.
PREPARE_SECONDS = 10


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
        segments.append(
            Segment(
                kind="prepare",
                duration_seconds=PREPARE_SECONDS,
                label="Prepárate",
                total_rounds=rounds,
            )
        )

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


def build_segments(job: JobV2) -> Optional[List[Segment]]:
    """Secuencia de segmentos cronometrados para un job.

    Devuelve None si el modo del job aún no tiene executor driven (el llamador
    puede entonces caer al modo descriptivo).
    """
    if job.mode in (JobModeV2.INTERVAL, JobModeV2.TABATA):
        return _interval_segments(job)
    return None
