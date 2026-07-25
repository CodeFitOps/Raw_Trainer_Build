# tests/test_driven.py
"""Tests del executor driven: construcción de segmentos (sin cronómetros)."""
from __future__ import annotations

from src.domain_v2.workout_v2 import JobV2, JobModeV2, ExerciseV2
from src.application.driven.executors import build_segments, PREPARE_SECONDS


def _interval_job():
    return JobV2(
        name="hiit",
        mode=JobModeV2.INTERVAL,
        rounds=8,
        work_time_in_seconds=40,
        rest_time_in_seconds=20,
        exercises=[ExerciseV2(name="A"), ExerciseV2(name="B"), ExerciseV2(name="C")],
    )


def test_interval_segments_structure():
    segs = build_segments(_interval_job())
    assert segs is not None
    # 1 prepare + 8 work + 7 rest (sin descanso tras la última ronda) = 16
    assert segs[0].kind == "prepare"
    assert segs[0].duration_seconds == PREPARE_SECONDS
    work = [s for s in segs if s.kind == "work"]
    rest = [s for s in segs if s.kind == "rest"]
    assert len(work) == 8
    assert len(rest) == 7
    assert work[0].duration_seconds == 40
    assert rest[0].duration_seconds == 20


def test_interval_exercises_rotate():
    work = [s for s in build_segments(_interval_job()) if s.kind == "work"]
    assert [w.exercise for w in work[:4]] == ["A", "B", "C", "A"]


def test_tabata_supported():
    job = JobV2(
        name="tab",
        mode=JobModeV2.TABATA,
        rounds=8,
        work_time_in_seconds=20,
        rest_time_in_seconds=10,
        exercises=[ExerciseV2(name="Burpees")],
    )
    segs = build_segments(job)
    assert segs is not None
    assert len([s for s in segs if s.kind == "work"]) == 8


def test_unsupported_mode_returns_none():
    job = JobV2(
        name="x",
        mode=JobModeV2.CUSTOM_SETS,
        rounds=3,
        exercises=[ExerciseV2(name="A", reps=10)],
    )
    assert build_segments(job) is None
