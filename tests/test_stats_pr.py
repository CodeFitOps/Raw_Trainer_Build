# tests/test_stats_pr.py
"""Test de la agregación de marcas/PRs por (workout, job)."""
from __future__ import annotations

from src.infrastructure.stats_v2 import collect_prs

RECORDS = [
    {"workout_name": "Fran", "stages": [{"jobs": [
        {"name": "Fran", "mode": "FT", "result_time_seconds": 300},
    ]}]},
    {"workout_name": "Fran", "stages": [{"jobs": [
        {"name": "Fran", "mode": "FT", "result_time_seconds": 280},
    ]}]},
    {"workout_name": "EDT", "stages": [{"jobs": [
        {"name": "density", "mode": "EDT", "result_total_reps": 80},
    ]}]},
    {"workout_name": "EDT", "stages": [{"jobs": [
        {"name": "density", "mode": "EDT", "result_total_reps": 92},
    ]}]},
]


def test_time_pr_is_minimum():
    prs = {(p.workout_name, p.job_name): p for p in collect_prs(RECORDS)}
    fran = prs[("Fran", "Fran")]
    assert fran.best == 280           # menor tiempo = mejor
    assert fran.attempts == 2
    assert fran.higher_better is False


def test_reps_pr_is_maximum():
    prs = {(p.workout_name, p.job_name): p for p in collect_prs(RECORDS)}
    edt = prs[("EDT", "density")]
    assert edt.best == 92             # más reps = mejor
    assert edt.attempts == 2
    assert edt.higher_better is True


def test_empty_records():
    assert collect_prs([]) == []
