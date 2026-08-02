# tests/test_estimate.py
"""Workout time estimate: per-job timing + between-job/stage rest (defaults and
the new stage/job rest fields)."""
from __future__ import annotations

from src.domain_v2.workout_v2 import WorkoutV2, JobV2
from src.application import estimate as E


def _job(**over):
    d = {"name": "j", "mode": "custom_sets", "rounds": 1,
         "rest_between_exercises_in_seconds": 0,
         "exercises": [{"name": "A", "work_time_in_seconds": 30}]}
    d.update(over)
    return d


def test_timed_job_uses_prepare_plus_work():
    job = JobV2.from_dict({
        "name": "h", "mode": "custom_sets", "rounds": 1,
        "rest_between_exercises_in_seconds": 0,
        "exercises": [{"name": "A", "work_time_in_seconds": 30},
                      {"name": "B", "work_time_in_seconds": 30}],
    })
    assert E.estimate_job_seconds(job) == E.PREPARE_SECONDS + 60


def test_default_rest_assumed_between_jobs():
    wk = WorkoutV2.from_dict({"name": "W", "stages": [
        {"name": "S1", "jobs": [_job(name="j1"), _job(name="j2")]},
    ]})
    est = E.estimate_workout(wk)
    assert est["work"] == 2 * (E.PREPARE_SECONDS + 30)
    assert est["rest"] == E.REST_BETWEEN_JOBS_DEFAULT      # one gap, assumed
    assert est["assumed_rest"] is True
    assert est["total"] == est["work"] + est["rest"]


def test_defined_rest_overrides_default():
    wk = WorkoutV2.from_dict({"name": "W", "stages": [
        {"name": "S1", "rest_between_jobs_in_seconds": 10, "jobs": [
            _job(name="j1"),
            _job(name="j2", rest_after_in_seconds=5),
            _job(name="j3"),
        ]},
    ]})
    est = E.estimate_workout(wk)
    # j1->j2: stage default 10 · j2->j3: job override 5
    assert est["rest"] == 15
    assert est["assumed_rest"] is False


def test_stage_rest_after_between_stages():
    wk = WorkoutV2.from_dict({"name": "W", "stages": [
        {"name": "S1", "rest_after_in_seconds": 20, "jobs": [_job()]},
        {"name": "S2", "jobs": [_job()]},
    ]})
    est = E.estimate_workout(wk)
    assert est["rest"] == 20
    assert est["assumed_rest"] is False


def test_fmt_duration():
    assert E.fmt_duration(0) == "0s"
    assert E.fmt_duration(90) == "1 min 30s"
    assert E.fmt_duration(120) == "2 min"
    assert E.fmt_duration(3600) == "1h 00m"
