import os
import sys

# Añadimos la carpeta src al sys.path de forma explícita
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT_DIR, "src")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import pytest

from domain.workout_model import Exercise
from domain.workout_errors import ExerciseValidationError


def test_exercise_from_dict_with_reps_only():
    data = {
        "NAME": "Push-ups",
        "reps": 10,
        "help": "Full ROM",
    }

    ex = Exercise.from_dict(data)

    assert ex.name == "Push-ups"
    assert ex.reps == 10
    assert ex.work_time_in_seconds is None
    assert ex.weight is None
    assert ex.help == "Full ROM"


def test_exercise_from_dict_with_time_only():
    data = {
        "NAME": "Plank",
        "work_time_in_seconds": 30,
    }

    ex = Exercise.from_dict(data)

    assert ex.name == "Plank"
    assert ex.reps is None
    assert ex.work_time_in_seconds == 30


def test_exercise_from_dict_requires_name():
    data = {
        "reps": 10,
    }

    with pytest.raises(ExerciseValidationError) as excinfo:
        Exercise.from_dict(data)

    assert "missing required field 'NAME'" in str(excinfo.value)


def test_exercise_from_dict_requires_reps_or_time():
    data = {
        "NAME": "No Reps Or Time",
    }

    with pytest.raises(ExerciseValidationError) as excinfo:
        Exercise.from_dict(data)

    assert "at least one of 'reps' or 'work_time_in_seconds'" in str(excinfo.value)


def test_exercise_from_dict_rejects_non_int_reps():
    data = {
        "NAME": "Bad Reps Type",
        "reps": "10",
    }

    with pytest.raises(ExerciseValidationError) as excinfo:
        Exercise.from_dict(data)

    assert "must be an integer" in str(excinfo.value)