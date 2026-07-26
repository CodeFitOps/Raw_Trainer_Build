# src/application/driven/scoring.py
"""Scoring/PR simple leyendo los records de sesión guardados.

`best_previous` devuelve la mejor marca previa de un score_key para un
workout+job concretos. Sirve para comparar la marca actual (densidad de EDT,
rondas de Death-By, tiempo de for_time, rondas de amrap) con el histórico.
"""
from __future__ import annotations

from typing import Iterable, Optional


def best_previous(
    records: Iterable[dict],
    workout_name: str,
    job_name: str,
    score_key: str,
    *,
    higher_better: bool = True,
) -> Optional[float]:
    """Mejor valor previo de `score_key` para (workout_name, job_name).

    higher_better=True  -> devuelve el MÁXIMO (densidad, rondas, reps).
    higher_better=False -> devuelve el MÍNIMO (tiempo: menos es mejor).
    None si no hay marcas previas válidas.
    """
    best: Optional[float] = None
    for rec in records:
        if not isinstance(rec, dict) or rec.get("workout_name") != workout_name:
            continue
        for stage in rec.get("stages", []) or []:
            if not isinstance(stage, dict):
                continue
            for job in stage.get("jobs", []) or []:
                if not isinstance(job, dict) or job.get("name") != job_name:
                    continue
                v = job.get(score_key)
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    continue
                if best is None:
                    best = v
                elif higher_better and v > best:
                    best = v
                elif not higher_better and v < best:
                    best = v
    return best
