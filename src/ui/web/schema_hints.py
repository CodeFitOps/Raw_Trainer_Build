# src/ui/web/schema_hints.py
"""Distill the JSON Schemas into a compact key/required map for the editor autocomplete.

Single source of truth: this reads internal_tools/schemas/*.json at request time, so the
client's key hints can never drift from the real validation. Web-only, no app deps beyond
the standard library — unit-testable in isolation against a schema directory.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

MODES = ["custom_sets", "tabata", "emom", "amrap", "for_time", "edt", "ladder", "interval", "carry"]


def _resolve(root: Dict[str, Any], ref: str) -> Dict[str, Any]:
    node: Any = root
    for part in ref.lstrip("#/").split("/"):
        if part:
            node = (node or {}).get(part, {})
    return node if isinstance(node, dict) else {}


def _merged(schema: Dict[str, Any], root: Dict[str, Any]) -> Tuple[List[str], List[str], Dict[str, Any]]:
    """Keys + required for an object schema, merging $ref and allOf branches."""
    props: Dict[str, Any] = {}
    req: List[str] = []

    def visit(s: Any) -> None:
        if not isinstance(s, dict):
            return
        ref = s.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/"):
            visit(_resolve(root, ref))
        for k, v in (s.get("properties") or {}).items():
            props.setdefault(k, v)
        for r in (s.get("required") or []):
            req.append(r)
        for sub in (s.get("allOf") or []):
            visit(sub)

    visit(schema)
    return list(props.keys()), sorted(set(req)), props


def _exercise_of(job_props: Dict[str, Any], root: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    ex = job_props.get("exercises")
    if isinstance(ex, dict) and isinstance(ex.get("items"), dict):
        keys, req, _ = _merged(ex["items"], root)
        return keys, req
    return [], []


def _effective_required(schema: Dict[str, Any], base_req: List[str]) -> List[str]:
    """Keys a *default* instance must set to validate — what a starter skeleton should pre-fill.

    Plain ``required`` misses two conditional shapes the job schemas use, so a naive skeleton
    silently produces invalid jobs. This folds them in:
      • ``if/then/else`` whose ``if`` gates on an optional variant key: a default omits that key,
        so the ``else`` branch's ``required`` applies (e.g. emom needs ``rounds`` unless
        ``death_by`` is set).
      • a root ``anyOf``/``oneOf`` requirement group where one branch must hold: take the first
        branch's keys (e.g. amrap needs ``work_time_in_minutes`` OR ``work_time_in_seconds``).
    """
    req = set(base_req)
    el = schema.get("else")
    if isinstance(el, dict):
        req |= set(el.get("required") or [])
    for grp in ("anyOf", "oneOf"):
        branches = schema.get(grp)
        if isinstance(branches, list):
            for b in branches:
                if isinstance(b, dict) and b.get("required"):
                    req |= set(b["required"])
                    break  # one branch satisfies the group
    return sorted(req)


def build_hints(schema_root: Path) -> Dict[str, Any]:
    """Compact {workout, stage, exercise, modes, job:{byMode}} map from the schemas."""
    out: Dict[str, Any] = {"job": {"byMode": {}}, "modes": MODES + ["super_sets"]}

    wk = json.loads((schema_root / "workout.schema.json").read_text(encoding="utf-8"))
    wk_keys, wk_req, wk_props = _merged(wk, wk)
    out["workout"] = {"keys": wk_keys, "required": wk_req}

    stages = wk_props.get("stages")
    if isinstance(stages, dict) and isinstance(stages.get("items"), dict):
        sk, sr, _ = _merged(stages["items"], wk)
        out["stage"] = {"keys": sk, "required": sr}
    else:
        out["stage"] = {"keys": ["name", "description", "tags", "jobs"], "required": ["name", "jobs"]}

    ex_keys: Dict[str, Any] = {}
    ex_req: List[str] = []
    for m in MODES:
        fn = schema_root / f"job.{m}.schema.json"
        if not fn.exists():
            continue
        js = json.loads(fn.read_text(encoding="utf-8"))
        jk, jr, jp = _merged(js, js)
        ek, er = _exercise_of(jp, js)
        # keep the mode's own exercise shape so the UI can show / suggest only the
        # fields valid for exercises in *this* mode (they differ: tabata needs reps,
        # carry surfaces distance_in_meters, custom_sets adds percent_1rm/rpe/…).
        out["job"]["byMode"][m] = {"keys": jk, "required": jr, "req_skel": _effective_required(js, jr), "exercise": {"keys": ek, "required": sorted(set(er))}}
        for k in ek:
            ex_keys.setdefault(k, True)
        ex_req += er

    out["job"]["byMode"]["super_sets"] = out["job"]["byMode"].get("custom_sets")
    out["exercise"] = {"keys": list(ex_keys.keys()) or ["name"], "required": sorted(set(ex_req)) or ["name"]}
    return out
