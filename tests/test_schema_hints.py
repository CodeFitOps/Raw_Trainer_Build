# tests/test_schema_hints.py
"""The editor's mode skeletons must pre-fill exactly the keys a valid default job needs.

Plain top-level `required` misses two conditional shapes the job schemas use, so these tests
lock `_effective_required` / the `req_skel` it feeds into: emom (rounds required via if/then/else
unless death_by is set) and amrap (one work-time field required via a root anyOf).
"""
from __future__ import annotations

import json

from src.ui.web.schema_hints import _effective_required, build_hints


def test_effective_required_folds_else_branch():
    # emom shape: `if death_by → then {} else → required rounds`. A default skeleton omits
    # death_by, so rounds becomes required.
    schema = {"required": ["exercises", "mode", "name"],
              "if": {"required": ["death_by"]}, "then": {}, "else": {"required": ["rounds"]}}
    assert _effective_required(schema, ["exercises", "mode", "name"]) == \
        ["exercises", "mode", "name", "rounds"]


def test_effective_required_folds_anyof_first_branch():
    # amrap shape: one of two work-time fields must be present. First branch is chosen.
    schema = {"required": ["exercises", "mode", "name"],
              "anyOf": [{"required": ["work_time_in_minutes"]}, {"required": ["work_time_in_seconds"]}]}
    out = _effective_required(schema, ["exercises", "mode", "name"])
    assert "work_time_in_minutes" in out and "work_time_in_seconds" not in out


def test_effective_required_plain_is_unchanged():
    schema = {"required": ["exercises", "mode", "name", "rounds"]}
    assert _effective_required(schema, ["exercises", "mode", "name", "rounds"]) == \
        ["exercises", "mode", "name", "rounds"]


def _write(d, name, obj):
    (d / name).write_text(json.dumps(obj), encoding="utf-8")


def test_build_hints_exposes_req_skel(tmp_path):
    _write(tmp_path, "workout.schema.json", {
        "type": "object", "required": ["name", "stages"],
        "properties": {"name": {"type": "string"},
                       "stages": {"type": "array", "items": {
                           "type": "object", "required": ["name", "jobs"],
                           "properties": {"name": {"type": "string"}, "jobs": {"type": "array"}}}}}})
    ex = {"type": "array", "items": {"type": "object", "required": ["name", "reps"],
          "properties": {"name": {"type": "string"}, "reps": {"type": "integer"}}}}
    _write(tmp_path, "job.emom.schema.json", {
        "type": "object", "required": ["exercises", "mode", "name"],
        "properties": {"name": {"type": "string"}, "mode": {"type": "string"},
                       "rounds": {"type": "integer"}, "death_by": {"type": "boolean"}, "exercises": ex},
        "if": {"required": ["death_by"]}, "then": {}, "else": {"required": ["rounds"]}})
    _write(tmp_path, "job.amrap.schema.json", {
        "type": "object", "required": ["exercises", "mode", "name"],
        "properties": {"name": {"type": "string"}, "mode": {"type": "string"},
                       "work_time_in_minutes": {"type": "integer"},
                       "work_time_in_seconds": {"type": "integer"}, "exercises": ex},
        "anyOf": [{"required": ["work_time_in_minutes"]}, {"required": ["work_time_in_seconds"]}]})
    _write(tmp_path, "job.custom_sets.schema.json", {
        "type": "object", "required": ["exercises", "mode", "name", "rounds"],
        "properties": {"name": {"type": "string"}, "mode": {"type": "string"},
                       "rounds": {"type": "integer"}, "exercises": ex}})

    by = build_hints(tmp_path)["job"]["byMode"]
    # emom: rounds folded in from the else-branch
    assert "rounds" in by["emom"]["req_skel"]
    assert "rounds" not in by["emom"]["required"]  # plain required still pure
    # amrap: a work-time field folded in from the anyOf
    assert "work_time_in_minutes" in by["amrap"]["req_skel"]
    # plain mode: req_skel is just the top-level required
    assert by["custom_sets"]["req_skel"] == by["custom_sets"]["required"]
