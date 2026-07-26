# src/ui/cli/builder.py
"""Interactive wizard to assemble a workout YAML step by step.

Thin skin over the application layer: uses `application.builder` for each mode's
fields/validation and `application.components` to reuse saved stages and jobs —
by exact name (finds one) or by tag (lists, you pick). Asks for tags at
workout/stage/job level. Returns a workout dict ready to validate/save (or None
if cancelled). All visible text goes through i18n (`t`).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.application import builder as appbuilder
from src.application import components
from src.application import library
from src.i18n import t
from src.ui.cli.style import prompt, title, info, error, success


# ---------------------------------------------------------------------------
# Basic prompts (EOFError/KeyboardInterrupt -> None = cancel)
# ---------------------------------------------------------------------------

def _input(text: str) -> Optional[str]:
    try:
        return input(prompt(text)).strip()
    except (EOFError, KeyboardInterrupt):
        return None


def _yesno(question: str, default: bool = True) -> bool:
    d = t("common.yes_no_yes") if default else t("common.yes_no")
    r = _input(f"{question} [{d}]: ")
    if r is None:
        return False
    if not r:
        return default
    return r.lower() in ("s", "si", "sí", "y", "yes")


def _required(label: str) -> Optional[str]:
    while True:
        v = _input(f"{label}: ")
        if v is None:
            return None
        if v:
            return v
        print(error(t("builder.required")))


def _optional(label: str) -> str:
    v = _input(f"{label}: ")
    return v or ""


def _prompt_tags(label: str) -> List[str]:
    raw = _input(t("builder.tags_suffix", label=label))
    if not raw:
        return []
    return [x.strip() for x in raw.split() if x.strip()]


def _field(label: str, typ: str, required: bool) -> Optional[Any]:
    hint = t("builder.hint_required") if required else t("builder.hint_skip")
    while True:
        raw = _input(f"{label} ({typ}, {hint}): ")
        if raw is None:
            return None
        if not raw:
            if required:
                print(error(t("builder.field_required")))
                continue
            return None
        try:
            return appbuilder.cast_value(raw, typ)
        except ValueError:
            print(error(t("builder.invalid_field", typ=typ)))


def _pick_mode() -> Optional[str]:
    modes = appbuilder.list_modes(library.SCHEMA_ROOT)
    print(info(t("builder.modes_available", modes=", ".join(modes))))
    while True:
        v = _input(t("builder.ask_mode"))
        if v is None:
            return None
        v = v.lower()
        if v in modes:
            return v
        print(error(t("builder.invalid_mode", modes=", ".join(modes))))


# ---------------------------------------------------------------------------
# Reusing components: by exact name or by tag
# ---------------------------------------------------------------------------

def _reuse_by_name(kind: str) -> Optional[Dict[str, Any]]:
    names = components.stage_names() if kind == "stage" else components.job_names()
    if not names:
        print(info(t("builder.no_components")))
        return None
    name = _input(t("builder.ask_exact_name", kind=kind))
    if not name:
        return None
    getter = components.get_stage if kind == "stage" else components.get_job
    data = getter(name)
    if data is None:
        print(error(t("builder.not_found", name=name)))
        return None
    return data


def _reuse_by_tag(kind: str) -> Optional[Dict[str, Any]]:
    raw = _input(t("builder.ask_tags_search"))
    if not raw:
        return None
    tags = [x for x in raw.split() if x]
    matcher = components.stages_by_tag if kind == "stage" else components.jobs_by_tag
    matches = matcher(tags)
    if not matches:
        print(info(t("builder.none_with_tags", kind=kind)))
        return None
    print(info(t("builder.matches_header", kind=kind, tags=", ".join(tags))))
    for i, n in enumerate(matches, start=1):
        print(f"    {i}) {n}")
    sel = _input(t("builder.ask_number"))
    if not sel or not sel.isdigit():
        return None
    idx = int(sel)
    if not (1 <= idx <= len(matches)):
        return None
    getter = components.get_stage if kind == "stage" else components.get_job
    return getter(matches[idx - 1])


def _reuse_choice(kind: str):
    """(action, data): 'cancel' | 'reuse'+dict | 'new'. If reuse finds nothing,
    falls through to 'new'."""
    print(info(t("builder.reuse_line", kind=kind)))
    c = _input(t("builder.ask_option"))
    if c is None:
        return ("cancel", None)
    c = c.strip().lower()
    if c == "r":
        data = _reuse_by_name(kind)
        return ("reuse", data) if data else ("new", None)
    if c == "t":
        data = _reuse_by_tag(kind)
        return ("reuse", data) if data else ("new", None)
    return ("new", None)


# ---------------------------------------------------------------------------
# Build by level
# ---------------------------------------------------------------------------

def _build_exercise(mode: str) -> Optional[Dict[str, Any]]:
    name = _required(t("builder.ex_name"))
    if name is None:
        return None
    ex: Dict[str, Any] = {"name": name}
    for f in appbuilder.exercise_scalar_fields(mode, library.SCHEMA_ROOT):
        val = _field(f"      {f['key']}", f["type"], f["required"])
        if val is not None:
            ex[f["key"]] = val
    return ex


def _build_job() -> Optional[Dict[str, Any]]:
    action, data = _reuse_choice("job")
    if action == "cancel":
        return None
    if action == "reuse":
        print(info(t("builder.job_reused", mode=data.get("mode", "?"))))
        return data

    name = _required(t("builder.job_name"))
    if name is None:
        return None
    # Auto-offer if the name matches a saved one exactly.
    if name in components.job_names():
        if _yesno(t("builder.job_exists", name=name), default=True):
            saved = components.get_job(name)
            if saved:
                print(info(t("builder.reused_mode", mode=saved.get("mode", "?"))))
                return saved

    mode = _pick_mode()
    if mode is None:
        return None
    job: Dict[str, Any] = {"name": name, "mode": mode}
    tags = _prompt_tags(t("builder.job_tags"))
    if tags:
        job["tags"] = tags
    for f in appbuilder.mode_scalar_fields(mode, library.SCHEMA_ROOT):
        val = _field(f"    {f['key']}", f["type"], f["required"])
        if val is not None:
            job[f["key"]] = val
    exercises: List[Dict[str, Any]] = []
    while _yesno(t("builder.add_exercise", n=len(exercises) + 1), default=True):
        ex = _build_exercise(mode)
        if ex is None:
            break
        exercises.append(ex)
    job["exercises"] = exercises
    print(info(t("builder.note_yaml_fields")))
    return job


def _build_stage() -> Optional[Dict[str, Any]]:
    action, data = _reuse_choice("stage")
    if action == "cancel":
        return None
    if action == "reuse":
        print(info(t("builder.stage_reused", n=len(data.get("jobs", []) or []))))
        return data

    name = _required(t("builder.stage_name"))
    if name is None:
        return None
    if name in components.stage_names():
        if _yesno(t("builder.stage_exists", name=name), default=True):
            saved = components.get_stage(name)
            if saved:
                print(info(t("builder.reused_jobs", n=len(saved.get("jobs", []) or []))))
                return saved

    stage: Dict[str, Any] = {"name": name}
    tags = _prompt_tags(t("builder.stage_tags"))
    if tags:
        stage["tags"] = tags
    desc = _optional(t("builder.stage_desc"))
    if desc:
        stage["description"] = desc
    jobs: List[Dict[str, Any]] = []
    while _yesno(t("builder.add_job", n=len(jobs) + 1, name=name), default=True):
        j = _build_job()
        if j is None:
            break
        jobs.append(j)
    stage["jobs"] = jobs
    return stage


def build_workout_interactive() -> Optional[Dict[str, Any]]:
    """Run the wizard and return the workout dict (or None if cancelled)."""
    print(title(t("builder.title")))
    name = _required(t("builder.workout_name"))
    if name is None:
        return None
    workout: Dict[str, Any] = {"name": name}
    tags = _prompt_tags(t("builder.workout_tags"))
    if tags:
        workout["tags"] = tags
    desc = _optional(t("builder.workout_desc"))
    if desc:
        workout["description"] = desc
    stages: List[Dict[str, Any]] = []
    while _yesno(t("builder.add_stage", n=len(stages) + 1), default=True):
        st = _build_stage()
        if st is None:
            break
        stages.append(st)
    workout["stages"] = stages
    return workout
