# tests/test_workout_v2.py
"""Tests del pipeline v2: validación JSON Schema + modelo de dominio WorkoutV2."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from src.application.workout_loader import (
    load_workout_v2_model_from_file,
    WorkoutLoadError,
)
from src.domain_v2.workout_v2 import JobModeV2, WorkoutV2

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "internal_tools" / "schemas"


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "workout.yaml"
    p.write_text(textwrap.dedent(text), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# JobModeV2.from_raw
# ---------------------------------------------------------------------------

def test_from_raw_canonical_and_synonyms():
    assert JobModeV2.from_raw("custom_sets") is JobModeV2.CUSTOM_SETS
    assert JobModeV2.from_raw("CUSTOM") is JobModeV2.CUSTOM_SETS
    assert JobModeV2.from_raw("super_sets") is JobModeV2.CUSTOM_SETS
    assert JobModeV2.from_raw("tabata") is JobModeV2.TABATA
    assert JobModeV2.from_raw("emom") is JobModeV2.EMOM
    assert JobModeV2.from_raw("amrap") is JobModeV2.AMRAP
    assert JobModeV2.from_raw("for_time") is JobModeV2.FOR_TIME
    assert JobModeV2.from_raw("edt") is JobModeV2.EDT
    assert JobModeV2.from_raw("ladder") is JobModeV2.LADDER
    assert JobModeV2.from_raw("interval") is JobModeV2.INTERVAL
    assert JobModeV2.from_raw("hiit") is JobModeV2.INTERVAL
    assert JobModeV2.from_raw("carry") is JobModeV2.CARRY
    assert JobModeV2.from_raw("hold") is JobModeV2.CARRY


def test_from_raw_rejects_unknown():
    with pytest.raises(ValueError):
        JobModeV2.from_raw("not_a_mode")


# ---------------------------------------------------------------------------
# Pipeline completo: validar + construir modelo
# ---------------------------------------------------------------------------

VALID = """
    name: Test WOD
    description: prueba
    stages:
      - name: Main
        jobs:
          - name: A
            mode: custom_sets
            rounds: 2
            exercises:
              - name: Push Ups
                reps: 10
          - name: B
            mode: tabata
            rounds: 8
            work_time_in_seconds: 20
            rest_time_in_seconds: 10
            exercises:
              - name: Air Squats
                reps: 15
"""


def test_load_valid_workout(tmp_path):
    w = load_workout_v2_model_from_file(path=_write(tmp_path, VALID), schema_root=SCHEMAS)
    assert isinstance(w, WorkoutV2)
    assert w.name == "Test WOD"
    assert len(w.stages) == 1
    jobs = w.stages[0].jobs
    assert [j.mode for j in jobs] == [JobModeV2.CUSTOM_SETS, JobModeV2.TABATA]
    assert jobs[0].exercises[0].name == "Push Ups"
    assert jobs[0].exercises[0].reps == 10


def test_synonyms_are_normalized(tmp_path):
    w = load_workout_v2_model_from_file(
        path=_write(tmp_path, """
            name: Syn
            stages:
              - name: S
                jobs:
                  - name: chip
                    mode: FORTIME
                    description: para completar lo antes posible
                    exercises:
                      - name: Burpees
                        reps: 20
                  - name: sup
                    mode: super_sets
                    rounds: 3
                    exercises:
                      - name: Curl
                        reps: 12
        """),
        schema_root=SCHEMAS,
    )
    modes = [j.mode for s in w.stages for j in s.jobs]
    assert JobModeV2.FOR_TIME in modes          # FORTIME -> for_time
    assert JobModeV2.CUSTOM_SETS in modes       # super_sets -> custom_sets


def test_ladder_supported(tmp_path):
    w = load_workout_v2_model_from_file(
        path=_write(tmp_path, """
            name: Lad
            stages:
              - name: S
                jobs:
                  - name: burpee ladder
                    mode: LADDER
                    total_rounds: 5
                    exercises:
                      - name: Burpees
                        reps: 1
        """),
        schema_root=SCHEMAS,
    )
    assert w.stages[0].jobs[0].mode is JobModeV2.LADDER


def test_interval_supported(tmp_path):
    w = load_workout_v2_model_from_file(
        path=_write(tmp_path, """
            name: Int
            stages:
              - name: S
                jobs:
                  - name: hiit
                    mode: interval
                    rounds: 8
                    work_time_in_seconds: 40
                    rest_time_in_seconds: 20
                    exercises:
                      - name: Air Squats
        """),
        schema_root=SCHEMAS,
    )
    assert w.stages[0].jobs[0].mode is JobModeV2.INTERVAL


def test_carry_supported(tmp_path):
    w = load_workout_v2_model_from_file(
        path=_write(tmp_path, """
            name: Carry
            stages:
              - name: S
                jobs:
                  - name: farmers
                    mode: carry
                    rounds: 3
                    exercises:
                      - name: Farmer's Walk
                        distance_in_meters: 40
                        weight: 32
                  - name: planks
                    mode: hold
                    rounds: 3
                    exercises:
                      - name: Plank
                        work_time_in_seconds: 60
        """),
        schema_root=SCHEMAS,
    )
    jobs = w.stages[0].jobs
    assert jobs[0].mode is JobModeV2.CARRY
    assert jobs[1].mode is JobModeV2.CARRY   # hold -> carry
    assert jobs[0].exercises[0].distance_in_meters == 40


def test_rejects_invalid_mode(tmp_path):
    with pytest.raises(WorkoutLoadError):
        load_workout_v2_model_from_file(
            path=_write(tmp_path, """
                name: Bad
                stages:
                  - name: S
                    jobs:
                      - name: J
                        mode: not_a_mode
                        rounds: 1
                        exercises:
                          - name: X
                            reps: 1
            """),
            schema_root=SCHEMAS,
        )


def test_rejects_missing_required(tmp_path):
    # custom_sets requiere 'rounds'
    with pytest.raises(WorkoutLoadError):
        load_workout_v2_model_from_file(
            path=_write(tmp_path, """
                name: Bad2
                stages:
                  - name: S
                    jobs:
                      - name: J
                        mode: custom_sets
                        exercises:
                          - name: X
                            reps: 1
            """),
            schema_root=SCHEMAS,
        )
