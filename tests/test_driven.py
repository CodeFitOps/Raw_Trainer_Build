# tests/test_driven.py
"""Tests del executor driven: construcción de segmentos (sin cronómetros)."""
from __future__ import annotations

from src.domain_v2.workout_v2 import (
    JobV2, JobModeV2, ExerciseV2, DeathBySpecV2, IntraSetV2,
)
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


def test_empty_job_returns_empty_segments():
    # Todos los modos tienen ya executor driven; un job sin ejercicios
    # no produce segmentos (y no revienta).
    job = JobV2(name="x", mode=JobModeV2.CUSTOM_SETS, rounds=3, exercises=[])
    assert build_segments(job) == []


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
    # build_segments no lo maneja: lo conduce _drive_death_by en el player.
    assert build_segments(job) is None


def test_edt_segments():
    job = JobV2(
        name="edt", mode=JobModeV2.EDT, work_time_in_minutes=15,
        exercises=[ExerciseV2(name="Bench", weight=40), ExerciseV2(name="Row", weight=40)],
    )
    segs = build_segments(job)
    assert segs is not None
    density = [s for s in segs if s.kind == "density"]
    assert len(density) == 1
    assert density[0].duration_seconds == 15 * 60
    assert density[0].items  # lista los ejercicios


def test_edt_seconds_override():
    job = JobV2(
        name="edt", mode=JobModeV2.EDT, work_time_in_seconds=45,
        exercises=[ExerciseV2(name="Bench", weight=40)],
    )
    density = [s for s in build_segments(job) if s.kind == "density"][0]
    assert density.duration_seconds == 45


def test_custom_sets_guided():
    job = JobV2(
        name="cs", mode=JobModeV2.CUSTOM_SETS, rounds=2,
        rest_between_exercises_in_seconds=5, rest_between_rounds_in_seconds=8,
        exercises=[
            ExerciseV2(name="Squat", reps=5, weight=60),
            ExerciseV2(name="Plank", work_time_in_seconds=10),
        ],
    )
    segs = build_segments(job)
    assert segs is not None
    # Squat = serie a tu ritmo (set) x2 rondas; Plank = hold cronometrado (work) x2.
    assert len([s for s in segs if s.kind == "set"]) == 2
    work = [s for s in segs if s.kind == "work"]
    assert len(work) == 2
    assert work[0].duration_seconds == 10
    # Hay descansos (entre ejercicios y entre rondas).
    assert any(s.kind == "rest" for s in segs)


def test_carry_guided():
    job = JobV2(
        name="c", mode=JobModeV2.CARRY, rounds=2, rest_between_rounds_in_seconds=30,
        exercises=[
            ExerciseV2(name="Farmer", distance_in_meters=40, weight=32),
            ExerciseV2(name="Plank", work_time_in_seconds=30),
        ],
    )
    segs = build_segments(job)
    assert segs is not None
    # Farmer (distancia) = self-paced set; Plank (tiempo) = work cronometrado.
    assert any(s.kind == "set" for s in segs)
    assert any(s.kind == "work" and s.duration_seconds == 30 for s in segs)


def test_ladder_guided():
    job = JobV2(
        name="l", mode=JobModeV2.LADDER,
        exercises=[ExerciseV2(name="Burpees", reps=1)],
        extra={"total_rounds": 5, "ladder_type": "ASCENDING", "increment_by": 1},
    )
    segs = build_segments(job)
    assert segs is not None
    sets = [s for s in segs if s.kind == "set"]
    assert len(sets) == 5  # 5 peldaños
    assert "1 reps" in sets[0].items[0]
    assert "5 reps" in sets[4].items[0]


def test_intra_set_rest_pause_expansion():
    ex = ExerciseV2(
        name="Bench", reps=13, weight=60,
        intra_set=IntraSetV2(type="rest_pause", rest_seconds=15, mini_sets=[8, 3, 2]),
    )
    job = JobV2(name="rp", mode=JobModeV2.CUSTOM_SETS, rounds=1, exercises=[ex])
    segs = build_segments(job)
    assert segs is not None
    assert len([s for s in segs if s.kind == "set"]) == 3          # 3 mini-esfuerzos
    intra_rests = [s for s in segs if s.kind == "rest" and s.duration_seconds == 15]
    assert len(intra_rests) == 2                                    # 2 descansos intra


def test_intra_set_drop_no_rest():
    ex = ExerciseV2(
        name="Curl", reps=10, weight=20,
        intra_set=IntraSetV2(type="drop_set",
                             drops=[{"weight": 20, "reps": 10}, {"weight": 15, "reps": 8}]),
    )
    job = JobV2(name="drop", mode=JobModeV2.CUSTOM_SETS, rounds=1, exercises=[ex])
    segs = build_segments(job)
    assert len([s for s in segs if s.kind == "set"]) == 2          # 2 bajadas
    assert [s for s in segs if s.kind == "rest"] == []             # sin descanso entre drops
