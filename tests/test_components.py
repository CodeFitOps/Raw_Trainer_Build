# tests/test_components.py
"""Test de la biblioteca de componentes (stages y jobs reutilizables)."""
from __future__ import annotations

from src.application import components

WORKOUT = {
    "name": "W",
    "stages": [
        {"name": "WU", "description": "warmup", "jobs": [
            {"name": "circuit", "mode": "custom_sets", "rounds": 2,
             "exercises": [{"name": "Squat", "reps": 10}]},
        ]},
        {"name": "Main", "jobs": [
            {"name": "Fran", "mode": "for_time", "description": "d",
             "exercises": [{"name": "Thruster", "reps": 21}]},
        ]},
    ],
}


def test_save_extract_and_get(tmp_path, monkeypatch):
    monkeypatch.setattr(components, "_project_root", lambda: tmp_path)
    counts = components.save_components_from_workout(WORKOUT)
    assert counts == {"stages": 2, "jobs": 2}
    assert set(components.stage_names()) == {"WU", "Main"}
    assert set(components.job_names()) == {"circuit", "Fran"}
    stage = components.get_stage("WU")
    assert stage["name"] == "WU"
    assert stage["jobs"][0]["name"] == "circuit"
    job = components.get_job("Fran")
    assert job["mode"] == "for_time"


def test_get_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(components, "_project_root", lambda: tmp_path)
    assert components.get_stage("nope") is None
    assert components.job_names() == []
