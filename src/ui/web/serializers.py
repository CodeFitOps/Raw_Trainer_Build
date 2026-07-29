# src/ui/web/serializers.py
"""Domain -> JSON. Sin lógica de negocio: solo forma de datos para el front.

Los nombres de campo son EXACTAMENTE los del dominio v2 (workout_v2.py) y los
de Segment (driven/segments.py), para que el front hable el mismo idioma que
la CLI y no haya un segundo modelo que mantener.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.application.driven.executors import build_segments
from src.domain_v2.workout_v2 import JobModeV2, JobV2, StageV2, WorkoutV2

# Modos que la CLI puntúa al terminar el job (player._capture_job_result).
SCORED_MODES = (JobModeV2.AMRAP, JobModeV2.EDT, JobModeV2.FOR_TIME)


def exercise_to_dict(ex) -> Dict[str, Any]:
    return {
        "name": ex.name,
        "reps": ex.reps,
        "work_time_in_seconds": ex.work_time_in_seconds,
        "distance_in_meters": ex.distance_in_meters,
        "weight": ex.weight,
        "percent_1rm": ex.percent_1rm,
        "rpe": ex.rpe,
        "notes": ex.notes,
        "sets": [
            {
                "reps": s.reps,
                "work_time_in_seconds": s.work_time_in_seconds,
                "weight": s.weight,
                "percent_1rm": s.percent_1rm,
                "rpe": s.rpe,
            }
            for s in (ex.sets or [])
        ],
        "intra_set": (
            {
                "type": ex.intra_set.type,
                "rest_seconds": ex.intra_set.rest_seconds,
                "mini_sets": ex.intra_set.mini_sets,
                "drops": ex.intra_set.drops,
            }
            if ex.intra_set
            else None
        ),
    }


def job_to_dict(job: JobV2) -> Dict[str, Any]:
    return {
        "name": job.name,
        "mode": job.mode.value,
        "mode_label": job.mode.mode_label(),
        "mode_description": job.mode.mode_description(),
        "description": job.description,
        "tags": job.tags,
        "rounds": job.rounds,
        "work_time_in_seconds": job.work_time_in_seconds,
        "work_time_in_minutes": job.work_time_in_minutes,
        "interval_in_seconds": job.interval_in_seconds,
        "rest_time_in_seconds": job.rest_time_in_seconds,
        "rest_between_exercises_in_seconds": job.rest_between_exercises_in_seconds,
        "rest_between_rounds_in_seconds": job.rest_between_rounds_in_seconds,
        "cadence": job.cadence,
        "tempo": job.tempo,
        "eccentric_neg": job.eccentric_neg,
        "isometric_hold": job.isometric_hold,
        "death_by": ({"increment_by": job.death_by.increment_by} if job.death_by else None),
        "exercises": [exercise_to_dict(e) for e in (job.exercises or [])],
        "scored": job.mode in SCORED_MODES,
    }


def stage_to_dict(stage: StageV2) -> Dict[str, Any]:
    return {
        "name": stage.name,
        "description": stage.description,
        "tags": stage.tags,
        "jobs": [job_to_dict(j) for j in stage.jobs],
    }


def workout_to_dict(workout: WorkoutV2) -> Dict[str, Any]:
    return {
        "name": workout.name,
        "description": workout.description,
        "tags": workout.tags,
        "n_stages": len(workout.stages),
        "n_jobs": sum(len(s.jobs) for s in workout.stages),
        "stages": [stage_to_dict(s) for s in workout.stages],
    }


def segment_to_dict(seg) -> Dict[str, Any]:
    return {
        "kind": seg.kind,
        "duration_seconds": seg.duration_seconds,
        "label": seg.label,
        "exercise": seg.exercise,
        "round_index": seg.round_index,
        "total_rounds": seg.total_rounds,
        "items": list(seg.items or []),
    }


def _manual_segment(job: JobV2) -> Dict[str, Any]:
    """Modo sin executor driven: un tramo a tu ritmo (equivale al fallback de player.py)."""
    return {
        "kind": "set",
        "duration_seconds": 0,
        "label": job.name,
        "exercise": None,
        "round_index": 0,
        "total_rounds": 0,
        "items": [],
        "manual": True,
    }


def build_timeline(workout: WorkoutV2, *, driven: bool = True) -> List[Dict[str, Any]]:
    """Lista plana que el player del navegador reproduce tal cual.

    Un nodo `brief` por job (ficha + START), los segmentos del executor, y un
    nodo `result` para los modos que la CLI puntúa.
    """
    timeline: List[Dict[str, Any]] = []
    for s_idx, stage in enumerate(workout.stages, start=1):
        for j_idx, job in enumerate(stage.jobs, start=1):
            base = {
                "stage_index": s_idx,
                "stage_name": stage.name,
                "stages_total": len(workout.stages),
                "job_index": j_idx,
                "jobs_in_stage": len(stage.jobs),
            }
            job_dict = job_to_dict(job)
            timeline.append({**base, "type": "brief", "job": job_dict})

            segments: Optional[list] = build_segments(job) if driven else None
            if segments:
                for seg in segments:
                    timeline.append({**base, "type": "seg", "job": job_dict,
                                     "seg": segment_to_dict(seg)})
            else:
                timeline.append({**base, "type": "seg", "job": job_dict,
                                 "seg": _manual_segment(job)})

            if job.mode in SCORED_MODES:
                timeline.append({**base, "type": "result", "job": job_dict})
    return timeline
