# tests/test_driven.py
"""Tests del executor driven: construcción de segmentos (sin cronómetros)."""
from __future__ import annotations

from src.domain_v2.workout_v2 import JobV2, JobModeV2, ExerciseV2, DeathBySpecV2
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


def test_amrap_window():
    job = JobV2(
        name="a", mode=JobModeV2.AMRAP, work_time_in_minutes=12,
        exercises=[ExerciseV2(name="Burpees", reps=15)],
    )
    segs = build_segments(job)
    assert segs is not None
    window = [s for s in segs if s.kind == "window"]
    assert len(window) == 1
    assert window[0].duration_seconds == 12 * 60
    assert window[0].items  # muestra el circuito


def test_amrap_seconds_override():
    job = JobV2(
        name="a", mode=JobModeV2.AMRAP, work_time_in_seconds=30,
        exercises=[ExerciseV2(name="Burpees", reps=15)],
    )
    window = [s for s in build_segments(job) if s.kind == "window"][0]
    assert window.duration_seconds == 30


def test_for_time_stopwatch():
    job = JobV2(
        name="ft", mode=JobModeV2.FOR_TIME,
        exercises=[ExerciseV2(name="Thrusters", reps=21)],
    )
    segs = build_segments(job)
    assert segs is not None
    sw = [s for s in segs if s.kind == "stopwatch"]
    assert len(sw) == 1
    assert sw[0].items


def test_emom_segments():
    job = JobV2(
        name="e", mode=JobModeV2.EMOM, rounds=5, interval_in_seconds=90,
        exercises=[ExerciseV2(name="Clean", reps=3, weight=70)],
    )
    work = [s for s in build_segments(job) if s.kind == "work"]
    assert len(work) == 5
    assert work[0].duration_seconds == 90


def test_emom_death_by_falls_back():
    job = JobV2(
        name="db", mode=JobModeV2.EMOM, interval_in_seconds=60,
        death_by=DeathBySpecV2(increment_by=1),
        exercises=[ExerciseV2(name="Burpees", reps=1)],
    )
    assert build_segments(job) is None  # Death-By aún sin executor driven
