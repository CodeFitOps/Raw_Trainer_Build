# tests/test_builder.py
"""Test de la capa de aplicación del builder (specs de campos + validación)."""
from __future__ import annotations

import pytest

from src.application import builder
from src.application.library import SCHEMA_ROOT


def test_list_modes():
    modes = builder.list_modes(SCHEMA_ROOT)
    for m in ("custom_sets", "for_time", "emom", "amrap", "interval", "edt", "carry", "ladder"):
        assert m in modes


def test_mode_scalar_fields_custom_sets():
    fields = builder.mode_scalar_fields("custom_sets", SCHEMA_ROOT)
    by_key = {f["key"]: f for f in fields}
    assert "rounds" in by_key and by_key["rounds"]["required"] is True
    assert by_key["rounds"]["type"] == "int"
    assert "cadence" in by_key and by_key["cadence"]["required"] is False
    # name / mode / exercises no son campos escalares a rellenar aquí
    assert "name" not in by_key and "exercises" not in by_key
    # los requeridos van primero
    assert fields[0]["required"] is True


def test_exercise_scalar_fields():
    keys = {f["key"] for f in builder.exercise_scalar_fields("custom_sets", SCHEMA_ROOT)}
    assert "reps" in keys
    assert "weight" in keys
    assert "name" not in keys


def test_cast_value():
    assert builder.cast_value("5", "int") == 5
    assert builder.cast_value("2.5", "float") == 2.5
    assert builder.cast_value("true", "bool") is True
    assert builder.cast_value("n", "bool") is False
    assert builder.cast_value("Push Ups", "str") == "Push Ups"
    with pytest.raises(ValueError):
        builder.cast_value("abc", "int")


def test_validate_workout_dict_valid():
    w = {"name": "T", "stages": [{"name": "S", "jobs": [
        {"name": "j", "mode": "custom_sets", "rounds": 2,
         "exercises": [{"name": "Squat", "reps": 10}]},
    ]}]}
    assert builder.validate_workout_dict(w, SCHEMA_ROOT) is None


def test_validate_workout_dict_invalid_missing_rounds():
    w = {"name": "T", "stages": [{"name": "S", "jobs": [
        {"name": "j", "mode": "custom_sets",
         "exercises": [{"name": "Squat", "reps": 10}]},
    ]}]}
    assert builder.validate_workout_dict(w, SCHEMA_ROOT) is not None
