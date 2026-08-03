# tests/test_errors.py
"""The web layer turns a raw WorkoutLoadError into a clean, located message:
no internal /tmp paths, and for YAML syntax errors the exact line/column + hint.
"""
from __future__ import annotations

import yaml

from src.ui.web.errors import clean_validation_error


class SchemaValidationError(Exception):
    pass


class WorkoutLoadError(Exception):
    pass


def _wrapped_yaml_error(text: str) -> WorkoutLoadError:
    """Reproduce exactly how the loader double-wraps a YAML syntax error."""
    try:
        yaml.safe_load(text)
        raise AssertionError("expected a YAML error")
    except yaml.YAMLError as ye:
        sve = SchemaValidationError(f"YAML syntax error in /tmp/x/check.yaml: {ye}")
        sve.__cause__ = ye
        wle = WorkoutLoadError(
            f"Workout in /tmp/x/check.yaml is invalid according to JSON Schemas: {sve}"
        )
        wle.__cause__ = sve
        return wle


def test_yaml_error_is_clean_and_located():
    bad = "name: X\ndescription: A + B: c\nstages: []\n"
    msg, detail = clean_validation_error(_wrapped_yaml_error(bad), bad)
    assert "/tmp" not in msg
    assert detail["kind"] == "yaml"
    assert detail["line"] == 2
    assert detail["snippet"] and "^" in detail["snippet"]
    assert detail["hint"]


def test_schema_error_strips_paths_and_schema_name():
    sve = SchemaValidationError(
        "/tmp/x/check.yaml: workout.schema.json: at STAGES/0/JOBS/0: 'name' is a required property"
    )
    wle = WorkoutLoadError(
        f"Workout in /tmp/x/check.yaml is invalid according to JSON Schemas: {sve}"
    )
    wle.__cause__ = sve
    msg, detail = clean_validation_error(wle)
    assert "/tmp" not in msg and ".schema.json" not in msg
    assert "required property" in msg
    assert detail["kind"] == "schema"


def test_schema_error_keeps_job_context():
    sve = SchemaValidationError(
        "Stage 1, job 2, mode='amrap': job.amrap.schema.json: at <root>: 'x' is a required property"
    )
    wle = WorkoutLoadError(
        f"Workout in /tmp/z/check.yaml is invalid according to JSON Schemas: {sve}"
    )
    wle.__cause__ = sve
    msg, _ = clean_validation_error(wle)
    assert "Stage 1, job 2" in msg
    assert ".schema.json" not in msg and "<root>" not in msg
