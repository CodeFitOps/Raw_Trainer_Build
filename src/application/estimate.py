# src/application/estimate.py
"""Rough time estimate for a workout — shown after the summary.

Per-job time reuses the driven executor's timed segments (so it lines up with
the real driven run), plus assumptions for the self-paced / open parts:
  · a self-paced set (reps)  ~ PER_SET seconds
  · a for_time block         ~ total reps × PER_REP
  · a Death-By               ~ DEATHBY_ROUNDS intervals

Rest BETWEEN jobs and BETWEEN stages isn't fixed by the model yet, so a default
is assumed unless defined:
  · stage.rest_between_jobs_in_seconds  → default rest between jobs in that stage
  · job.rest_after_in_seconds           → rest after that job (overrides the stage)
  · stage.rest_after_in_seconds         → rest after that stage (between stages)
"""
from __future__ import annotations

from typing import Dict

from src.application.driven.executors import build_segments, PREPARE_SECONDS
from src.domain_v2.workout_v2 import JobModeV2, JobV2, WorkoutV2

PER_SET = 40                        # a self-paced set (reps + setup), seconds
PER_REP = 3                         # a rep, for for_time estimates
DEATHBY_ROUNDS = 8                  # assumed rounds survived in a Death-By
REST_BETWEEN_JOBS_DEFAULT = 120     # 2 min (no model field defined)
REST_BETWEEN_STAGES_DEFAULT = 120   # 2 min


def _total_reps(job: JobV2) -> int:
    total = 0
    for ex in (job.exercises or []):
        sets = list(getattr(ex, "sets", None) or [])
        if sets:
            for st in sets:
                r = getattr(st, "reps", None)
                if isinstance(r, int):
                    total += r
        elif isinstance(getattr(ex, "reps", None), int):
            total += ex.reps
    return total


def estimate_job_seconds(job: JobV2) -> int:
    """Rough seconds for one job (timed parts exact, self-paced parts assumed)."""
    if job.mode is JobModeV2.EMOM and job.death_by is not None:
        interval = job.interval_in_seconds or job.work_time_in_seconds or 60
        return PREPARE_SECONDS + interval * DEATHBY_ROUNDS

    segs = build_segments(job) or []
    total = 0
    for s in segs:
        if s.duration_seconds:
            total += s.duration_seconds            # prepare / work / rest / window…
        elif s.kind == "set":
            total += PER_SET                        # self-paced reps
        elif s.kind == "stopwatch":                 # for_time — open-ended
            reps = _total_reps(job)
            total += reps * PER_REP if reps else 5 * 60
    return total


def estimate_workout(workout: WorkoutV2) -> Dict[str, int]:
    """{'work','rest','total','assumed_rest'} — seconds, plus whether any
    between-job/stage rest fell back to the default."""
    work = 0
    rest = 0
    assumed = False
    stages = workout.stages or []
    for si, stage in enumerate(stages):
        stage_default = stage.rest_between_jobs_in_seconds
        jobs = stage.jobs or []
        for ji, job in enumerate(jobs):
            work += estimate_job_seconds(job)
            if ji < len(jobs) - 1:                  # rest before the next job
                if job.rest_after_in_seconds is not None:
                    rest += job.rest_after_in_seconds
                elif stage_default is not None:
                    rest += stage_default
                else:
                    rest += REST_BETWEEN_JOBS_DEFAULT
                    assumed = True
        if si < len(stages) - 1:                    # rest before the next stage
            if stage.rest_after_in_seconds is not None:
                rest += stage.rest_after_in_seconds
            else:
                rest += REST_BETWEEN_STAGES_DEFAULT
                assumed = True
    return {"work": work, "rest": rest, "total": work + rest, "assumed_rest": assumed}


def fmt_duration(seconds: int) -> str:
    seconds = max(0, int(round(seconds)))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m:02d}m"
    if m:
        return f"{m} min" if s == 0 else f"{m} min {s:02d}s"
    return f"{s}s"
