# src/ui/web/errors.py
"""Turn a raw WorkoutLoadError into a clean, user-facing validation message.

The loader wraps errors twice and bakes an internal /tmp path into the text
(`Workout in /tmp/.../check.yaml is invalid according to JSON Schemas: YAML
syntax error in /tmp/.../check.yaml: ...`). The original ``yaml.YAMLError`` — with
the exact line/column — survives in the ``__cause__`` chain, so for syntax errors
we surface line/column + a snippet + a hint instead of a parser dump; for schema
errors we strip the paths and schema filenames and keep the useful part.

Web-only: does not touch the loader or the CLI (which want the file path).
Depends on nothing from the app (only ``re`` + ``yaml``) so it is unit-testable
in isolation.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

import yaml


def _find_yaml_error(exc: BaseException) -> Optional[yaml.YAMLError]:
    """Walk the __cause__/__context__ chain looking for the original YAML error."""
    seen = set()
    cur: Optional[BaseException] = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        if isinstance(cur, yaml.YAMLError):
            return cur
        cur = cur.__cause__ or cur.__context__
    return None


def _yaml_hint(problem: str) -> Optional[str]:
    p = (problem or "").lower()
    if "mapping values are not allowed" in p:
        return "a value that contains ':' must be quoted — e.g.  name: \"Front squat: heavy\""
    if "could not find expected ':'" in p:
        return "check indentation and that each mapping key ends with ':'"
    if "tab" in p or "\\t" in p:
        return "use spaces for indentation, not tabs"
    if "expected <block end>" in p or "found unexpected" in p:
        return "check indentation — a line is probably indented wrong"
    return None


def _clean_schema_message(inner: BaseException) -> str:
    msg = str(inner)
    msg = re.sub(r"/\S+?\.ya?ml:?\s*", "", msg)          # internal tmp/abs file paths
    msg = re.sub(r"\S+\.schema\.json:\s*", "", msg)       # schema filenames
    msg = re.sub(r"at <root>:\s*", "", msg)               # noise for top-level errors
    msg = re.sub(r"is invalid according to JSON Schemas:\s*", "", msg)
    msg = re.sub(r"^Workout\s+in\s+", "", msg)
    msg = re.sub(r"\s{2,}", " ", msg).strip().strip(":").strip()
    return msg or "invalid workout"


def clean_validation_error(
    exc: BaseException, source_text: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """Return (human_message, structured_detail) for a validation failure.

    human_message is a clean (possibly multi-line) string ready to show in the
    console; structured_detail carries kind/line/column/snippet/hint for a UI
    that wants to render it richer later.
    """
    ye = _find_yaml_error(exc)
    if ye is not None:
        mark = getattr(ye, "problem_mark", None)
        problem = (getattr(ye, "problem", None) or "invalid YAML syntax").strip()
        line = (mark.line + 1) if mark is not None else None
        col = (mark.column + 1) if mark is not None else None
        snippet = None
        if source_text and line:
            rows = source_text.splitlines()
            if 1 <= line <= len(rows):
                caret = " " * (max(1, col or 1) - 1) + "^"
                snippet = rows[line - 1] + "\n" + caret
        hint = _yaml_hint(problem)
        head = "YAML syntax error"
        if line:
            head += f" · line {line}" + (f", col {col}" if col else "")
        parts = [f"{head}: {problem}"]
        if snippet:
            parts.append(snippet)
        if hint:
            parts.append("Hint: " + hint)
        detail = {"kind": "yaml", "message": problem, "line": line,
                  "column": col, "snippet": snippet, "hint": hint}
        return "\n".join(parts), detail

    inner = exc.__cause__ if exc.__cause__ is not None else exc
    msg = _clean_schema_message(inner)
    return msg, {"kind": "schema", "message": msg, "line": None,
                 "column": None, "snippet": None, "hint": None}
