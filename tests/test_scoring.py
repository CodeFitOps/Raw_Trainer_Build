# tests/test_scoring.py
"""Test del helper de PR/scoring (mejor marca previa por workout+job)."""
from __future__ import annotations

from src.application.driven.scoring import best_previous

RECORDS = [
    {"workout_name": "W", "stages": [{"jobs": [
        {"name": "edt", "result_total_reps": 80},
        {"name": "ft", "result_time_seconds": 300},
    ]}]},
    {"workout_name": "W", "stages": [{"jobs": [
        {"name": "edt", "result_total_reps": 92},
        {"name": "ft", "result_time_seconds": 280},
    ]}]},
    {"workout_name": "OTHER", "stages": [{"jobs": [
        {"name": "edt", "result_total_reps": 999},
    ]}]},
]


def test_best_previous_higher_is_max():
    assert best_previous(RECORDS, "W", "edt", "result_total_reps", higher_better=True) == 92


def test_best_previous_lower_is_min():
    assert best_previous(RECORDS, "W", "ft", "result_time_seconds", higher_better=False) == 280


def test_best_previous_none_when_absent():
    assert best_previous(RECORDS, "W", "nope", "result_total_reps") is None
    assert best_previous([], "W", "edt", "result_total_reps") is None


def test_best_previous_ignores_other_workout():
    # OTHER tiene 999 pero no pertenece al workout "W".
    assert best_previous(RECORDS, "W", "edt", "result_total_reps", higher_better=True) == 92
