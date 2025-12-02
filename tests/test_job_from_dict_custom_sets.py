# tests/test_job_from_dict_custom_sets.py

import os
import sys

import pytest

# --- bootstrap para que 'domain' sea importable desde tests ---

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# --- imports del dominio ---

from domain.workout_model import Job, JobMode  # type: ignore
from domain.workout_errors import JobValidationError  # type: ignore


def test_job_from_dict_custom_sets_valid_minimal():
    data = {
        "NAME": "Upper Body",
        "MODE": "custom_sets",
        "Rounds": 3,
        "EXERCISES": [
            {"NAME": "Push-ups", "reps": 10},
        ],
    }

    job = Job.from_dict_custom_sets(data)

    assert job.name == "Upper Body"
    assert job.mode is JobMode.CUSTOM_SETS
    assert job.rounds == 3
    assert len(job.exercises) == 1
    assert job.exercises[0].name == "Push-ups"
    assert job.exercises[0].reps == 10


def test_job_from_dict_custom_sets_with_optional_fields():
    data = {
        "NAME": "Legs Block",
        "MODE": "custom_sets",
        "Rounds": 4,
        "EXERCISES": [
            {"NAME": "Squats", "reps": 12},
        ],
        "description": "Legs work",
        "Rest_between_exercises_in_seconds": 10,
        "Rest_between_rounds_in_seconds": 60,
        "work_time_in_seconds": 30,
        "work_time_in_minutes": 1,
        "cadence": "3010",
        "Eccentric (NEG)": True,
        "isometric (HOLD)": False,
    }

    job = Job.from_dict_custom_sets(data)

    assert job.name == "Legs Block"
    assert job.rounds == 4
    assert job.description == "Legs work"
    assert job.rest_between_exercises_in_seconds == 10
    assert job.rest_between_rounds_in_seconds == 60
    assert job.work_time_in_seconds == 30
    assert job.work_time_in_minutes == 1
    assert job.cadence == "3010"
    assert job.eccentric_neg is True
    assert job.isometric_hold is False


def test_job_from_dict_custom_sets_requires_name():
    data = {
        "MODE": "custom_sets",
        "Rounds": 3,
        "EXERCISES": [
            {"NAME": "Push-ups", "reps": 10},
        ],
    }

    with pytest.raises(JobValidationError) as excinfo:
        Job.from_dict_custom_sets(data)

    assert "missing required field 'NAME'" in str(excinfo.value)


def test_job_from_dict_custom_sets_rejects_wrong_mode():
    data = {
        "NAME": "Upper Body",
        "MODE": "emom",
        "Rounds": 3,
        "EXERCISES": [
            {"NAME": "Push-ups", "reps": 10},
        ],
    }

    with pytest.raises(JobValidationError) as excinfo:
        Job.from_dict_custom_sets(data)

    assert "unsupported MODE 'emom'" in str(excinfo.value)


def test_job_from_dict_custom_sets_requires_rounds():
    data = {
        "NAME": "Upper Body",
        "MODE": "custom_sets",
        "EXERCISES": [
            {"NAME": "Push-ups", "reps": 10},
        ],
    }

    with pytest.raises(JobValidationError) as excinfo:
        Job.from_dict_custom_sets(data)

    assert "missing required field 'Rounds'" in str(excinfo.value)


@pytest.mark.parametrize("rounds_value", ["3", 0, -1])
def test_job_from_dict_custom_sets_rounds_must_be_positive_int(rounds_value):
    data = {
        "NAME": "Upper Body",
        "MODE": "custom_sets",
        "Rounds": rounds_value,
        "EXERCISES": [
            {"NAME": "Push-ups", "reps": 10},
        ],
    }

    with pytest.raises(JobValidationError):
        Job.from_dict_custom_sets(data)


def test_job_from_dict_custom_sets_requires_exercises():
    data = {
        "NAME": "Upper Body",
        "MODE": "custom_sets",
        "Rounds": 3,
    }

    with pytest.raises(JobValidationError) as excinfo:
        Job.from_dict_custom_sets(data)

    assert "missing required field 'EXERCISES'" in str(excinfo.value)


def test_job_from_dict_custom_sets_exercises_must_be_list():
    data = {
        "NAME": "Upper Body",
        "MODE": "custom_sets",
        "Rounds": 3,
        "EXERCISES": {"NAME": "Push-ups", "reps": 10},
    }

    with pytest.raises(JobValidationError) as excinfo:
        Job.from_dict_custom_sets(data)

    assert "must be a list" in str(excinfo.value)


def test_job_from_dict_custom_sets_exercises_must_not_be_empty():
    data = {
        "NAME": "Upper Body",
        "MODE": "custom_sets",
        "Rounds": 3,
        "EXERCISES": [],
    }

    with pytest.raises(JobValidationError) as excinfo:
        Job.from_dict_custom_sets(data)

    assert "must contain at least one item" in str(excinfo.value)


def test_job_from_dict_custom_sets_wraps_invalid_exercise_error():
    data = {
        "NAME": "Upper Body",
        "MODE": "custom_sets",
        "Rounds": 3,
        "EXERCISES": [
            {"reps": 10},  # falta NAME -> ExerciseValidationError dentro
        ],
    }

    with pytest.raises(JobValidationError) as excinfo:
        Job.from_dict_custom_sets(data)

    msg = str(excinfo.value)
    assert "invalid exercise at index 0" in msg
    assert "missing required field 'NAME'" in msg


def test_job_from_dict_custom_sets_rejects_invalid_optional_type():
    data = {
        "NAME": "Upper Body",
        "MODE": "custom_sets",
        "Rounds": 3,
        "EXERCISES": [
            {"NAME": "Push-ups", "reps": 10},
        ],
        "Rest_between_exercises_in_seconds": "10",
    }

    with pytest.raises(JobValidationError) as excinfo:
        Job.from_dict_custom_sets(data)

    assert "Rest_between_exercises_in_seconds" in str(excinfo.value)
    assert "must be an integer" in str(excinfo.value)