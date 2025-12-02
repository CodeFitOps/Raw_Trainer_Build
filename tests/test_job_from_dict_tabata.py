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


def _valid_tabata_job_dict() -> dict:
    return {
        "NAME": "TABATA",
        "MODE": "TABATA",
        "description": "TABATA JOB TEMPLATE",
        "rounds": 8,
        "work_time_in_seconds": 20,
        "rest_time_in_seconds": 10,
        "EXERCISES": [
            {"NAME": "Wall Balls", "reps": 50},
            {"NAME": "Deadlifts", "reps": 15, "weight": 35},
        ],
    }


def test_job_from_dict_tabata_valid_minimal():
    data = _valid_tabata_job_dict()
    job = Job.from_dict_tabata(data)

    assert job.name == "TABATA"
    assert job.mode.value == "TABATA"
    assert job.rounds == 8
    assert job.work_time_in_seconds == 20
    assert job.rest_time_in_seconds == 10
    assert len(job.exercises) == 2
    assert job.exercises[0].name == "Wall Balls"
    assert job.exercises[0].reps == 50


def test_job_from_dict_tabata_requires_mode_tabata():
    data = _valid_tabata_job_dict()
    data["MODE"] = "custom_sets"

    with pytest.raises(JobValidationError):
        Job.from_dict_tabata(data)


def test_job_from_dict_tabata_requires_positive_rounds():
    data = _valid_tabata_job_dict()
    data["rounds"] = 0

    with pytest.raises(JobValidationError):
        Job.from_dict_tabata(data)


def test_job_from_dict_tabata_requires_exercises_non_empty_list():
    data = _valid_tabata_job_dict()
    data["EXERCISES"] = []

    with pytest.raises(JobValidationError):
        Job.from_dict_tabata(data)


def test_job_from_dict_tabata_requires_reps_in_each_exercise():
    data = _valid_tabata_job_dict()
    # remove reps from first exercise
    del data["EXERCISES"][0]["reps"]

    with pytest.raises(JobValidationError):
        Job.from_dict_tabata(data)