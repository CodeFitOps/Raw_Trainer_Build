from __future__ import annotations

from pathlib import Path
from typing import Any
import re

# Optional dependency; validated at load time.
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


# =============================================================================
# Built-in default render schema
# =============================================================================

DEFAULT_RENDER_SCHEMA_YAML = """\
version: 1

defaults:
  indent_spaces: 2
  list:
    remove_dash: true

rules:
  - match: { key: name }
    render:
      show_label: false
      value: { role: name }

  - match: { key: description }
    render:
      show_label: false
      value: { role: plain }

  - match: { key: mode }
    render:
      show_label: true
      label: "MODE"
      value: { role: enum }

  - match: { key: cadence }
    render:
      show_label: true
      label: "CADENCE"
      value: { role: cadence }

  - match: { path: "stages[].jobs[].exercises" }
    render:
      as: exercise_lines
      show_label: false
      template: "{name}{reps}{time}{weight}"
      parts:
        name:
          from: name
          role: exercise_name
        reps:
          when_exists: reps
          format: " x {value}"
          role: number
        time:
          when_exists: work_time_in_seconds
          format: " for {value} secs"
          role: number
        weight:
          when_exists: weight
          format: " x {value} kg"
          role: number
"""


def load_default_render_schema_text() -> str:
    """Return the built-in render schema YAML text."""
    return DEFAULT_RENDER_SCHEMA_YAML


def load_render_schema_text(path: str | Path | None) -> tuple[str, str]:
    """
    Load render schema YAML text and return (text, source_label).

    - If path is None -> returns built-in DEFAULT_RENDER_SCHEMA_YAML and source 'DEFAULT'.
    - Else reads the file and returns its text and absolute path as source.
    """
    if path is None:
        return load_default_render_schema_text(), "DEFAULT"

    p = Path(path)
    if not p.exists():
        raise SystemExit(f"Render schema not found: {p}")
    return p.read_text(encoding="utf-8", errors="replace"), str(p.resolve())


# =============================================================================
# Schema parsing
# =============================================================================

def load_render_schema(text: str) -> dict[str, Any]:
    """Parse schema YAML into a dict; exits with a clear error if invalid."""
    if yaml is None:
        raise SystemExit("Missing dependency: PyYAML. Install with: pip install pyyaml")

    try:
        data = yaml.safe_load(text) or {}
    except Exception as e:
        raise SystemExit(f"Render schema YAML parse failed: {e}")

    if not isinstance(data, dict):
        raise SystemExit("Render schema must be a YAML mapping (dict).")

    return data


def render_defaults(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Extract defaults used by the renderer.

    Returns:
      {"indent_spaces": int, "list": dict}
    """
    defaults = schema.get("defaults") or {}
    if not isinstance(defaults, dict):
        defaults = {}

    list_defaults = defaults.get("list") or {}
    if not isinstance(list_defaults, dict):
        list_defaults = {}

    try:
        indent_spaces = int(defaults.get("indent_spaces", 2))
    except Exception:
        indent_spaces = 2

    return {"indent_spaces": indent_spaces, "list": list_defaults}


def _schema_rules_only(schema: dict[str, Any]) -> list[dict[str, Any]]:
    rules = schema.get("rules") or []
    if not isinstance(rules, list):
        raise SystemExit("render schema 'rules' must be a list.")
    return [r for r in rules if isinstance(r, dict)]


# =============================================================================
# Rule matching
# =============================================================================

_PATH_INDEX_RE = re.compile(r"\[\d+\]")


def _norm_path(path: str) -> str:
    # stages[0].jobs[2] -> stages[].jobs[]
    return _PATH_INDEX_RE.sub("[]", path)


def _norm_key(x: Any) -> str:
    return str(x).strip().lower()


def _match_path(pattern: str, canonical_path: str) -> bool:
    """
    Flexible path matcher.

    Accepts patterns like:
      stages[].jobs[].exercises
      stages[].jobs[].exercises[]
      stages[].jobs[]
    And compares them to canonical paths produced by the renderer, e.g.:
      stages[].jobs[].exercises[]
      stages[].jobs[]
    """
    p = (pattern or "").strip().replace(" ", "")
    c = (canonical_path or "").strip().replace(" ", "")
    if not p or not c:
        return False

    if p.endswith("."):
        p = p[:-1]

    # exact
    if p == c:
        return True

    # Allow "exercises" to match "exercises[]"
    p_segs = p.split(".")
    c_segs = c.split(".")
    if len(p_segs) != len(c_segs):
        return False

    for ps, cs in zip(p_segs, c_segs):
        if ps == cs:
            continue
        if (ps + "[]") == cs:
            continue
        return False
    return True


def _rule_score(rule: dict[str, Any]) -> int:
    """
    Priority:
      path+key : 300
      path     : 200
      key      : 100
      else     : 0
    """
    m = rule.get("match") or {}
    if not isinstance(m, dict):
        return 0
    has_path = bool(m.get("path"))
    has_key = bool(m.get("key"))
    if has_path and has_key:
        return 300
    if has_path:
        return 200
    if has_key:
        return 100
    return 0

def render_defaults(schema: dict[str, Any]) -> dict[str, Any]:
    defaults = schema.get("defaults") or {}
    if not isinstance(defaults, dict):
        defaults = {}

    list_defaults = defaults.get("list") or {}
    if not isinstance(list_defaults, dict):
        list_defaults = {}

    return {
        "indent_spaces": int(defaults.get("indent_spaces", 2)),
        "list": list_defaults,
    }

def render_rules(
    rules: list[dict[str, Any]],
    *,
    canonical_path: str,
    key: str | None = None,
) -> dict[str, Any] | None:
    """
    Select the best matching rule from a list of rules.

    Rules can match:
      - key-only
      - path-only
      - path+key

    The highest priority match is returned, with stable tie-breaker = first in file.
    """
    key_l = _norm_key(key) if key is not None else None
    cpath = _norm_path(canonical_path)

    best: tuple[int, int, dict[str, Any]] | None = None  # (score, index, rule)

    for idx, r in enumerate(rules):
        m = r.get("match") or {}
        if not isinstance(m, dict):
            continue

        m_key = m.get("key")
        m_path = m.get("path")

        # key check
        if m_key is not None:
            if key_l is None:
                continue
            if _norm_key(m_key) != key_l:
                continue

        # path check
        if m_path is not None:
            if not isinstance(m_path, str):
                continue
            if not _match_path(m_path, cpath):
                continue

        score = _rule_score(r)
        if best is None or score > best[0]:
            best = (score, idx, r)

    return best[2] if best else None


def find_path_rule(schema: dict[str, Any], canonical_path: str) -> dict[str, Any] | None:
    """
    Convenience: find a *path-only* rule for a container path.
    Intended for renderers like "as: exercise_lines" or "as: header_line".
    """
    rules = _schema_rules_only(schema)
    cpath = _norm_path(canonical_path)

    for r in rules:
        m = r.get("match") or {}
        if not isinstance(m, dict):
            continue
        rp = m.get("path")
        rk = m.get("key")
        if rk is not None:
            continue
        if isinstance(rp, str) and _match_path(rp, cpath):
            return r
    return None


def find_rule(
    schema: dict[str, Any],
    *,
    canonical_path: str,
    key: str | None,
) -> dict[str, Any] | None:
    """Convenience: select best rule from schema rules."""
    rules = _schema_rules_only(schema)
    return render_rules(rules, canonical_path=canonical_path, key=key)


# =============================================================================
# Backwards-compat aliases (temporary; remove once callers migrate)
# =============================================================================

_schema_load_yaml = load_render_schema
_schema_get_defaults = render_defaults
_schema_find_path_rule = find_path_rule
_schema_rules = _schema_rules_only
_find_rule = render_rules