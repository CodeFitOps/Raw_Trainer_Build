# tests/test_workout_from_dict.py

import os
import sys

import pytest

# --- bootstrap para que 'domain' sea importable desde tests ---

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# --- imports del dominio ---

from domain.workout_model import Workout, JobMode  # type: ignore
from domain.workout_errors import WorkoutTopLevelValidationError  # type: ignore


def _valid_stage_dict(name: str = "Warm-up") -> dict:
    return {
        "NAME": name,
        "JOBS": [
            {
                "NAME": "Upper Body",
                "MODE": "custom_sets",
                "Rounds": 3,
                "EXERCISES": [
                    {"NAME": "Push-ups", "reps": 10},
                ],
            }
        ],
    }


def test_workout_from_dict_valid_minimal():
    data = {
        "NAME": "Full Body A",
        "STAGES": [
            _valid_stage_dict("Warm-up"),
        ],
    }

    workout = Workout.from_dict(data)

    assert workout.name == "Full Body A"
    assert len(workout.stages) == 1

    stage = workout.stages[0]
    assert stage.name == "Warm-up"
    assert len(stage.jobs) == 1

    job = stage.jobs[0]
    assert job.name == "Upper Body"
    assert job.mode is JobMode.CUSTOM_SETS
    assert job.rounds == 3
    assert job.exercises[0].name == "Push-ups"


def test_workout_from_dict_with_description_and_multiple_stages():
    data = {
        "NAME": "Full Body B",
        "description": "Mixed strength and conditioning",
        "STAGES": [
            _valid_stage_dict("Warm-up"),
            _valid_stage_dict("Strength"),
        ],
    }

    workout = Workout.from_dict(data)

    assert workout.name == "Full Body B"
    assert workout.description == "Mixed strength and conditioning"
    assert len(workout.stages) == 2
    assert workout.stages[0].name == "Warm-up"
    assert workout.stages[1].name == "Strength"


def test_workout_from_dict_requires_name():
    data = {
        "STAGES": [
            _valid_stage_dict("Warm-up"),
        ],
    }

    with pytest.raises(WorkoutTopLevelValidationError) as excinfo:
        Workout.from_dict(data)

    assert "missing required field 'NAME'" in str(excinfo.value)


def test_workout_from_dict_requires_stages():
    data = {
        "NAME": "Full Body A",
    }

    with pytest.raises(WorkoutTopLevelValidationError) as excinfo:
        Workout.from_dict(data)

    assert "missing required field 'STAGES'" in str(excinfo.value)


def test_workout_from_dict_stages_must_be_list():
    data = {
        "NAME": "Full Body A",
        "STAGES": _valid_stage_dict("Warm-up"),  # no lista
    }

    with pytest.raises(WorkoutTopLevelValidationError) as excinfo:
        Workout.from_dict(data)

    assert "must be a list" in str(excinfo.value)


def test_workout_from_dict_stages_must_not_be_empty():
    data = {
        "NAME": "Full Body A",
        "STAGES": [],
    }

    with pytest.raises(WorkoutTopLevelValidationError) as excinfo:
        Workout.from_dict(data)

    assert "must contain at least one item" in str(excinfo.value)


def test_workout_from_dict_wraps_invalid_stage_error():
    # Stage inválido: falta 'JOBS'
    bad_stage = {
        "NAME": "Warm-up",
    }

    data = {
        "NAME": "Full Body A",
        "STAGES": [bad_stage],
    }

    with pytest.raises(WorkoutTopLevelValidationError) as excinfo:
        Workout.from_dict(data)

    msg = str(excinfo.value)
    assert "invalid stage at index 0" in msg
    assert "missing required field 'JOBS'" in msg


def test_workout_from_dict_rejects_invalid_description_type():
    data = {
        "NAME": "Full Body A",
        "description": 123,  # debe ser str
        "STAGES": [
            _valid_stage_dict("Warm-up"),
        ],
    }

    with pytest.raises(WorkoutTopLevelValidationError) as excinfo:
        Workout.from_dict(data)

    msg = str(excinfo.value)
    assert "field 'description' must be a string" in msg