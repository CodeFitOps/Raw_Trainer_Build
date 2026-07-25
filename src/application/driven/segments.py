# src/application/driven/segments.py
"""Segmento cronometrado: la unidad mínima que reproduce el player driven."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Segment:
    """Un tramo de tiempo con un significado.

    kind:
      - "prepare":   cuenta atrás inicial antes de empezar.
      - "work":      tramo de trabajo (un ejercicio durante duration_seconds).
      - "rest":      tramo de descanso.
      - "window":    ventana con cuenta atrás (AMRAP): repite el circuito.
      - "stopwatch": cronómetro ascendente que para el usuario (for_time).

    items: líneas a mostrar durante el segmento (p.ej. el circuito de un AMRAP
    o la lista de movimientos de un for_time).
    """
    kind: str
    duration_seconds: int
    label: str
    exercise: Optional[str] = None
    round_index: int = 0     # ronda 1..N (0 = preparación)
    total_rounds: int = 0
    items: Optional[List[str]] = None
