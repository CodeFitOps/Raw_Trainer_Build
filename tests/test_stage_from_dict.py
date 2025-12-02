# tests/test_stage_from_dict.py

import os
import sys

import pytest

# --- bootstrap para que 'domain' sea importable desde tests ---

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# --- imports del dominio ---

from domain.workout_model import Stage, JobMode  # type: ignore
from domain.workout_errors import StageValidationError  # type: ignore


def _valid_custom_sets_job_dict() -> dict:
    return {
        "NAME": "Upper Body",
        "MODE": "custom_sets",
        "Rounds": 3,
        "EXERCISES": [
            {"NAME": "Push-ups", "reps": 10},
        ],
    }


def test_stage_from_dict_valid_minimal():
    data = {
        "NAME": "Warm-up",
        "JOBS": [
            _valid_custom_sets_job_dict(),
        ],
    }

    stage = Stage.from_dict(data)

    assert stage.name == "Warm-up"
    assert len(stage.jobs) == 1
    job = stage.jobs[0]
    assert job.name == "Upper Body"
    assert job.mode is JobMode.CUSTOM_SETS
    assert job.rounds == 3
    assert job.exercises[0].name == "Push-ups"


def test_stage_from_dict_with_description():
    data = {
        "NAME": "Strength",
        "description": "Heavy work",
        "JOBS": [
            _valid_custom_sets_job_dict(),
        ],
    }

    stage = Stage.from_dict(data)

    assert stage.name == "Strength"
    assert stage.description == "Heavy work"
    assert len(stage.jobs) == 1


def test_stage_from_dict_requires_name():
    data = {
        "JOBS": [
            _valid_custom_sets_job_dict(),
        ],
    }

    with pytest.raises(StageValidationError) as excinfo:
        Stage.from_dict(data)

    assert "missing required field 'NAME'" in str(excinfo.value)


def test_stage_from_dict_requires_jobs():
    data = {
        "NAME": "Warm-up",
    }

    with pytest.raises(StageValidationError) as excinfo:
        Stage.from_dict(data)

    assert "missing required field 'JOBS'" in str(excinfo.value)


def test_stage_from_dict_jobs_must_be_list():
    data = {
        "NAME": "Warm-up",
        "JOBS": _valid_custom_sets_job_dict(),  # no lista
    }

    with pytest.raises(StageValidationError) as excinfo:
        Stage.from_dict(data)

    assert "must be a list" in str(excinfo.value)


def test_stage_from_dict_jobs_must_not_be_empty():
    data = {
        "NAME": "Warm-up",
        "JOBS": [],
    }

    with pytest.raises(StageValidationError) as excinfo:
        Stage.from_dict(data)

    assert "must contain at least one item" in str(excinfo.value)


def test_stage_from_dict_job_missing_mode():
    bad_job = _valid_custom_sets_job_dict()
    bad_job.pop("MODE")

    data = {
        "NAME": "Warm-up",
        "JOBS": [bad_job],
    }

    with pytest.raises(StageValidationError) as excinfo:
        Stage.from_dict(data)

    msg = str(excinfo.value)
    assert "missing required field 'MODE'" in msg


def test_stage_from_dict_job_with_unsupported_mode():
    bad_job = _valid_custom_sets_job_dict()
    bad_job["MODE"] = "emom"

    data = {
        "NAME": "Warm-up",
        "JOBS": [bad_job],
    }

    with pytest.raises(StageValidationError) as excinfo:
        Stage.from_dict(data)

    msg = str(excinfo.value)
    assert "unsupported MODE 'emom'" in msg


def test_stage_from_dict_wraps_invalid_job_error():
    bad_job = {
        "NAME": "Upper Body",
        "MODE": "custom_sets",
        # Falta 'Rounds' -> JobValidationError dentro
        "EXERCISES": [
            {"NAME": "Push-ups", "reps": 10},
        ],
    }

    data = {
        "NAME": "Warm-up",
        "JOBS": [bad_job],
    }

    with pytest.raises(StageValidationError) as excinfo:
        Stage.from_dict(data)

    msg = str(excinfo.value)
    assert "invalid job at index 0" in msg
    assert "missing required field 'Rounds'" in msg


def test_stage_from_dict_rejects_invalid_description_type():
    data = {
        "NAME": "Warm-up",
        "description": 123,  # debe ser str
        "JOBS": [
            _valid_custom_sets_job_dict(),
        ],
    }

    with pytest.raises(StageValidationError) as excinfo:
        Stage.from_dict(data)

    msg = str(excinfo.value)
    assert "field 'description' must be a string" in msg