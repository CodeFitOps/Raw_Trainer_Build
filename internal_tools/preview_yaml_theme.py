#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal

from rich.console import Console
from rich.rule import Rule
from rich.text import Text


DescriptionStyle = Literal["plain", "highlight"]


# =============================================================================
# Theme model (intuitivo + validado)
# =============================================================================

@dataclass(frozen=True)
class Palette:
    # Layout
    bg: str
    bg_alt: str

    # Plain text (only used when rules.use_terminal_fg == False)
    plain_fg: str | None  # e.g. "#dcdbdb"

    # Secondary
    dim: str  # comments / secondary

    # YAML roles
    key_name: str             # key name (left of :)
    value_name: str           # value for general NAME-like keys
    value_exercise_name: str  # value for name inside exercises (contextual)
    value_enum: str           # value for MODE-like keys (enums)
    value_number: str         # numbers
    bool_true: str            # True
    bool_false: str | None    # False (only colored if provided)
    null: str | None = None   # null (optional override)

    # cadence independent (optional; if None => cadence behaves as before)
    value_cadence: str | None = None

    # Optional: description highlight (only used if description_value == "highlight")
    value_description: str | None = None


@dataclass(frozen=True)
class Rules:
    # Key groups (mutually exclusive by validation except exercise_name (contextual))
    name_value_keys: tuple[str, ...] = ("name",)
    enum_value_keys: tuple[str, ...] = ("mode",)
    description_keys: tuple[str, ...] = ("description",)

    # cadence keys (independent from enum) - only applied if palette.value_cadence is set
    cadence_value_keys: tuple[str, ...] = ("cadence",)

    # exercises context
    exercise_list_keys: tuple[str, ...] = ("exercises",)
    exercise_name_keys: tuple[str, ...] = ("name",)

    # Description highlight behavior
    description_value: DescriptionStyle = "plain"
    description_block: DescriptionStyle = "plain"

    # Plain FG behavior
    use_terminal_fg: bool = True  # if False -> palette.plain_fg is used everywhere as base FG


@dataclass(frozen=True)
class ThemeSpec:
    name: str
    palette: Palette
    rules: Rules = Rules()


def _lower_set(xs: Iterable[str]) -> set[str]:
    return {x.strip().lower() for x in xs}


def validate_theme(t: ThemeSpec) -> None:
    p = t.palette
    r = t.rules

    required_strings = [
        ("bg", p.bg),
        ("bg_alt", p.bg_alt),
        ("dim", p.dim),
        ("key_name", p.key_name),
        ("value_name", p.value_name),
        ("value_exercise_name", p.value_exercise_name),
        ("value_enum", p.value_enum),
        ("value_number", p.value_number),
        ("bool_true", p.bool_true),
    ]
    missing = [name for name, val in required_strings if not isinstance(val, str) or not val.strip()]
    if missing:
        raise ValueError(f"[{t.name}] missing required palette fields: {', '.join(missing)}")

    if not r.use_terminal_fg:
        if not (p.plain_fg and isinstance(p.plain_fg, str) and p.plain_fg.strip()):
            raise ValueError(f"[{t.name}] rules.use_terminal_fg=False requires palette.plain_fg")

    if r.description_value == "highlight" and not (p.value_description and p.value_description.strip()):
        raise ValueError(f"[{t.name}] rules.description_value='highlight' requires palette.value_description")

    name_keys = _lower_set(r.name_value_keys)
    enum_keys = _lower_set(r.enum_value_keys)
    desc_keys = _lower_set(r.description_keys)
    cadence_keys = _lower_set(r.cadence_value_keys)

    overlaps = []
    if name_keys & enum_keys:
        overlaps.append(f"name_value_keys ∩ enum_value_keys = {sorted(name_keys & enum_keys)}")
    if name_keys & desc_keys:
        overlaps.append(f"name_value_keys ∩ description_keys = {sorted(name_keys & desc_keys)}")
    if enum_keys & desc_keys:
        overlaps.append(f"enum_value_keys ∩ description_keys = {sorted(enum_keys & desc_keys)}")
    if cadence_keys & name_keys:
        overlaps.append(f"cadence_value_keys ∩ name_value_keys = {sorted(cadence_keys & name_keys)}")
    if cadence_keys & enum_keys:
        overlaps.append(f"cadence_value_keys ∩ enum_value_keys = {sorted(cadence_keys & enum_keys)}")
    if cadence_keys & desc_keys:
        overlaps.append(f"cadence_value_keys ∩ description_keys = {sorted(cadence_keys & desc_keys)}")

    if overlaps:
        raise ValueError(f"[{t.name}] overlapping rule key sets: " + " | ".join(overlaps))


# =============================================================================
# Themes
# =============================================================================

THEMES: dict[str, ThemeSpec] = {
    "raw_yamltools_blue": ThemeSpec(
        name="raw_yamltools_blue",
        palette=Palette(
            bg="#252821",
            bg_alt="#3D4133",
            plain_fg="#dcdbdb",        # only used if use_terminal_fg=False
            dim="#A0A29D",
            key_name="#C62CFB",
            value_name="#C62CFB",      # (tu set actual; no lo toco)
            value_exercise_name="#2cfb5f",
            value_enum="#538df0",
            value_number="#2cfb5f",
            bool_true="#2cfb5f",
            bool_false="#FF3B30",
            null=None,
            value_description=None,
        ),
        rules=Rules(
            description_value="plain",
            description_block="plain",
            use_terminal_fg=False,
        ),
    ),

    "base_green_terminal": ThemeSpec(
        name="base_green_terminal",
        palette=Palette(
            bg="#08140E",
            bg_alt="#0F2A1B",
            plain_fg="#d7ddd8",
            dim="#6B8F7A",
            key_name="#00FF7A",
            value_name="#FFD166",
            value_exercise_name="#00E5FF",
            value_enum="#00D7FF",
            value_number="#00D7FF",
            bool_true="#B6FF00",
            bool_false="#FF3B30",
            null="#6B8F7A",
        ),
        rules=Rules(description_value="plain", description_block="plain", use_terminal_fg=True),
    ),

    "base_blue_terminal": ThemeSpec(
        name="base_blue_terminal",
        palette=Palette(
            bg="#07111F",
            bg_alt="#0E223D",
            plain_fg="#d7dde6",
            dim="#8AA0B8",
            key_name="#2D7DFF",
            value_name="#FFD166",
            value_exercise_name="#00E5FF",
            value_enum="#C62CFB",
            value_number="#C62CFB",
            bool_true="#00FF3B",
            bool_false="#FF3B30",
            null="#8AA0B8",
        ),
        rules=Rules(description_value="plain", description_block="plain", use_terminal_fg=True),
    ),

    "base_amber_terminal": ThemeSpec(
        name="base_amber_terminal",
        palette=Palette(
            bg="#15110A",
            bg_alt="#2A1E10",
            plain_fg="#e3d7c7",
            dim="#B59C7A",
            key_name="#FFB000",
            value_name="#D7E274",
            value_exercise_name="#00E5FF",
            value_enum="#00E5FF",
            value_number="#00E5FF",
            bool_true="#00FF3B",
            bool_false="#FF3B30",
            null="#B59C7A",
        ),
        rules=Rules(description_value="plain", description_block="plain", use_terminal_fg=True),
    ),

    "base_synth_purple": ThemeSpec(
        name="base_synth_purple",
        palette=Palette(
            bg="#140B1F",
            bg_alt="#2A1342",
            plain_fg="#e2d9f0",
            dim="#A99BC2",
            key_name="#FF4DFF",
            value_name="#FFE066",
            value_exercise_name="#00E5FF",
            value_enum="#00E5FF",
            value_number="#00E5FF",
            bool_true="#00FF3B",
            bool_false="#FF3B30",
            null="#A99BC2",
        ),
        rules=Rules(description_value="plain", description_block="plain", use_terminal_fg=True),
    ),

    "base_cyan_black": ThemeSpec(
        name="base_cyan_black",
        palette=Palette(
            bg="#000000",
            bg_alt="#141414",
            plain_fg="#C7C7C7",
            dim="#707070",
            key_name="#00FFFF",
            value_name="#C7C7C7",
            value_exercise_name="#00E5FF",
            value_enum="#00B7FF",
            value_number="#FF00FC",
            bool_true="#00FF3B",
            bool_false="#FF3B30",
            null="#707070",
        ),
        rules=Rules(description_value="plain", description_block="plain", use_terminal_fg=False),
    ),
}

for _t in THEMES.values():
    validate_theme(_t)


# =============================================================================
# Raw YAML-ish styling (modo actual)
# =============================================================================

KEY_RE = re.compile(r"^(\s*-\s*)?(\s*)(?P<key>(?:'[^']*'|\"[^\"]*\"|[^:#\n]+?))(\s*:)")
NUM_RE = re.compile(r"\b\d+\b")
BOOL_NULL_RE = re.compile(r"\b(true|false|null)\b", re.IGNORECASE)
BLOCK_SCALAR_RE = re.compile(r"^(?:[>|])(?:[+-])?$")


def build_console() -> Console:
    return Console(color_system="truecolor", force_terminal=True, soft_wrap=False)


def find_comment_start(s: str) -> int | None:
    in_single = False
    in_double = False
    escape = False
    for i, ch in enumerate(s):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == "'" and not in_double:
            in_single = not in_single
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            continue
        if ch == "#" and not in_single and not in_double:
            return i
    return None


def _value_span(line: str, colon_end: int | None, comment_limit: int) -> tuple[int, int] | None:
    if colon_end is None:
        return None
    vs = colon_end
    while vs < len(line) and line[vs] == " ":
        vs += 1
    if vs >= comment_limit:
        return None
    return vs, comment_limit


def _parse_key_line(line: str) -> tuple[str | None, int | None, int | None, str | None]:
    m = KEY_RE.match(line)
    if not m:
        return None, None, None, None

    k = m.group("key").rstrip()
    key_name = k.strip()
    if (key_name.startswith("'") and key_name.endswith("'")) or (key_name.startswith('"') and key_name.endswith('"')):
        key_name = key_name[1:-1].strip()

    colon_end = m.end(0)
    base_indent = len(line) - len(line.lstrip(" "))

    cpos = find_comment_start(line)
    comment_limit = cpos if cpos is not None else len(line)
    span = _value_span(line, colon_end, comment_limit)
    if not span:
        return key_name.lower(), colon_end, base_indent, ""
    vs, ve = span
    return key_name.lower(), colon_end, base_indent, line[vs:ve].strip()


def _base_style(theme: ThemeSpec) -> str:
    p = theme.palette
    r = theme.rules
    if r.use_terminal_fg:
        return f"on {p.bg}"
    return f"{p.plain_fg} on {p.bg}"


def style_line(
    rawline: str,
    theme: ThemeSpec,
    *,
    plain: bool = False,
    in_exercises_block: bool = False,
) -> Text:
    p = theme.palette
    r = theme.rules

    line = rawline.rstrip("\n")
    bg = p.bg

    t = Text(line, style=_base_style(theme))

    cpos = find_comment_start(line)
    comment_limit = len(line)
    if cpos is not None:
        t.stylize(f"{p.dim} on {bg}", cpos, len(line))
        comment_limit = cpos

    if plain:
        return t

    m = KEY_RE.match(line)
    key_name = None
    colon_end = None

    if m:
        k = m.group("key").rstrip()
        key_start = m.start("key")
        key_end = key_start + len(k)

        key_name = k.strip()
        if (key_name.startswith("'") and key_name.endswith("'")) or (
            key_name.startswith('"') and key_name.endswith('"')
        ):
            key_name = key_name[1:-1].strip()

        colon_end = m.end(0)

        if key_start < comment_limit:
            t.stylize(f"{p.key_name} on {bg}", key_start, min(key_end, comment_limit))

    if m and key_name:
        k_lower = key_name.lower()
        span = _value_span(line, colon_end, comment_limit)

        name_keys = _lower_set(r.name_value_keys)
        enum_keys = _lower_set(r.enum_value_keys)
        desc_keys = _lower_set(r.description_keys)
        cadence_keys = _lower_set(r.cadence_value_keys)
        exercise_name_keys = _lower_set(r.exercise_name_keys)

        if k_lower in desc_keys:
            if span and r.description_value == "highlight" and p.value_description:
                vs, ve = span
                t.stylize(f"{p.value_description} on {bg}", vs, ve)
            return t

        if p.value_cadence and (k_lower in cadence_keys):
            if span:
                vs, ve = span
                t.stylize(f"{p.value_cadence} on {bg}", vs, ve)
            return t

        if in_exercises_block and (k_lower in exercise_name_keys):
            if span:
                vs, ve = span
                t.stylize(f"{p.value_exercise_name} on {bg}", vs, ve)
            return t

        if k_lower in name_keys:
            if span:
                vs, ve = span
                t.stylize(f"{p.value_name} on {bg}", vs, ve)
            return t

        if k_lower in enum_keys:
            if span:
                vs, ve = span
                t.stylize(f"{p.value_enum} on {bg}", vs, ve)
            return t

    span = _value_span(line, colon_end, comment_limit)
    if span:
        vs, ve = span
        for nm in NUM_RE.finditer(line, vs, ve):
            t.stylize(f"{p.value_number} on {bg}", nm.start(), nm.end())

        for bm in BOOL_NULL_RE.finditer(line, vs, ve):
            token = bm.group(1).lower()
            if token == "true":
                t.stylize(f"{p.bool_true} on {bg}", bm.start(), bm.end())
            elif token == "false":
                if p.bool_false:
                    t.stylize(f"{p.bool_false} on {bg}", bm.start(), bm.end())
            else:
                null_color = p.null or p.dim
                t.stylize(f"{null_color} on {bg}", bm.start(), bm.end())

    return t


def _print_full_width(console: Console, text: Text, bg: str) -> None:
    pad = max(0, console.width - text.cell_len)
    if pad:
        text.append(" " * pad, style=f"on {bg}")
    console.print(text, highlight=False, no_wrap=True, overflow="crop")


def preview_yaml_text(text: str, theme: ThemeSpec) -> None:
    console = build_console()
    p = theme.palette
    r = theme.rules

    lines = text.splitlines(True)

    console.print(Rule(style=p.bg_alt))
    header = Text(style=_base_style(theme))
    header.append(" RawTrainer YAML Theme Preview ", style=f"{p.key_name} on {p.bg}")
    header.append(f"— {theme.name} ", style=f"{p.value_enum} on {p.bg}")
    _print_full_width(console, header, p.bg)
    console.print(Rule(style=p.bg_alt))

    in_desc_block = False
    desc_indent = 0
    desc_plain = (r.description_block == "plain")

    in_exercises_block = False
    exercises_indent = 0
    exercise_list_keys = _lower_set(r.exercise_list_keys)
    desc_keys = _lower_set(r.description_keys)

    for rawline in lines:
        line = rawline.rstrip("\n")

        if in_exercises_block and line.strip() != "":
            indent = len(line) - len(line.lstrip(" "))
            if indent <= exercises_indent:
                in_exercises_block = False

        if in_desc_block:
            if line.strip() == "":
                _print_full_width(console, style_line(rawline, theme, plain=True), p.bg)
                continue

            indent = len(line) - len(line.lstrip(" "))
            if indent > desc_indent:
                _print_full_width(console, style_line(rawline, theme, plain=desc_plain), p.bg)
                continue

            in_desc_block = False

        key_lower, _colon_end, base_indent, value_stripped = _parse_key_line(line)

        if key_lower in exercise_list_keys and base_indent is not None:
            span = (value_stripped or "").strip()
            if span == "":
                in_exercises_block = True
                exercises_indent = base_indent

        is_desc_block_start = (
            key_lower in desc_keys
            and value_stripped is not None
            and BLOCK_SCALAR_RE.match(value_stripped) is not None
        )

        _print_full_width(
            console,
            style_line(rawline, theme, plain=False, in_exercises_block=in_exercises_block),
            p.bg,
        )

        if is_desc_block_start and base_indent is not None:
            in_desc_block = True
            desc_indent = base_indent

    console.print(Rule(style=p.bg_alt))
    console.print()


# =============================================================================
# Render Schema (YAML DSL) for --human
# =============================================================================

DEFAULT_RENDER_SCHEMA_YAML = """\
version: 1

# Global defaults for the human renderer
defaults:
  indent_spaces: 2
  list:
    remove_dash: true

# Rules are matched by priority: path+key > path > key
rules:
  # Hide labels for top-level or generic keys
  - match: { key: name }
    render:
      show_label: false
      value: { role: name }

  - match: { key: description }
    render:
      show_label: false
      value: { role: plain }

  # MODE with enum role (color from palette.value_enum)
  - match: { key: mode }
    render:
      show_label: true
      label: "MODE"
      value: { role: enum }

  # CADENCE independent role (palette.value_cadence if set; else plain)
  - match: { key: cadence }
    render:
      show_label: true
      label: "CADENCE"
      value: { role: cadence }

  # Exercises: compact one-liner per exercise item
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


def _norm_key(x: Any) -> str:
    return str(x).strip().lower()


def _canonical_path_join(base: str, seg: str) -> str:
    return seg if not base else f"{base}.{seg}"


def _to_canonical_path_for_key(parent_path: str, key: str) -> str:
    return _canonical_path_join(parent_path, key)


def _to_canonical_path_for_list(parent_path: str, list_key: str) -> str:
    return _canonical_path_join(parent_path, f"{list_key}[]")


def _schema_load_yaml(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception:
        raise SystemExit("Missing dependency: PyYAML. Install with: pip install pyyaml")

    try:
        data = yaml.safe_load(text) or {}
    except Exception as e:
        raise SystemExit(f"Render schema YAML parse failed: {e}")

    if not isinstance(data, dict):
        raise SystemExit("Render schema must be a YAML mapping (dict).")

    return data


def _schema_get_list_defaults(schema: dict[str, Any]) -> dict[str, Any]:
    defaults = schema.get("defaults") or {}
    if not isinstance(defaults, dict):
        return {}
    list_defaults = defaults.get("list") or {}
    if not isinstance(list_defaults, dict):
        list_defaults = {}
    return {"indent_spaces": int(defaults.get("indent_spaces", 2)), "list": list_defaults}


def _schema_rules(schema: dict[str, Any]) -> list[dict[str, Any]]:
    rules = schema.get("rules") or []
    if not isinstance(rules, list):
        raise SystemExit("render schema 'rules' must be a list.")
    out: list[dict[str, Any]] = []
    for r in rules:
        if isinstance(r, dict):
            out.append(r)
    return out


def _match_path(pattern: str, canonical_path: str) -> bool:
    """
    pattern examples:
      stages[].jobs[].exercises
      stages[].jobs[].exercises.name
    canonical_path examples:
      stages[].jobs[].exercises[]
      stages[].jobs[].exercises[].name   (if you decide to match item fields)
    We currently generate canonical paths for dict keys and list containers with [].
    """
    p = pattern.strip()
    c = canonical_path.strip()
    if not p:
        return False

    # normalize user pattern:
    # - allow "exercises" to mean exercises[] container
    # - accept both 'exercises' and 'exercises[]'
    p = p.replace(" ", "")
    c = c.replace(" ", "")

    if p.endswith("."):
        p = p[:-1]

    # if user pattern ends with ".exercises" without [], we accept matching exercises[]
    if p.endswith(".exercises"):
        if c.endswith(".exercises[]"):
            return True

    # exact match
    if p == c:
        return True

    # Accept p without [] for list segments: convert "foo" -> "foo[]"
    # naive: split and map any seg that ends with "[]" keep; if seg exists as list in canonical must match.
    p_segs = p.split(".")
    c_segs = c.split(".")
    if len(p_segs) != len(c_segs):
        return False

    for ps, cs in zip(p_segs, c_segs):
        if ps == cs:
            continue
        # allow ps without [] to match cs with []
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


def _find_rule(
    rules: list[dict[str, Any]],
    *,
    canonical_path: str,
    key: str | None,
) -> dict[str, Any] | None:
    key_l = _norm_key(key) if key is not None else None
    best: tuple[int, int, dict[str, Any]] | None = None  # (score, index, rule)

    for idx, r in enumerate(rules):
        m = r.get("match") or {}
        if not isinstance(m, dict):
            continue

        m_key = m.get("key")
        m_path = m.get("path")

        if m_key is not None and key_l is not None:
            if _norm_key(m_key) != key_l:
                continue
        elif m_key is not None and key_l is None:
            continue

        if m_path is not None:
            if not isinstance(m_path, str) or not _match_path(m_path, canonical_path):
                continue

        score = _rule_score(r)
        cand = (score, -idx, r)  # earlier rules win on same score
        if best is None or cand > best:
            best = cand

    return best[2] if best else None


def _role_to_color(role: str | None, theme: ThemeSpec) -> str | None:
    if not role:
        return None
    p = theme.palette
    r = role.strip().lower()

    # common aliases
    if r in {"plain", "text", "terminal"}:
        return None
    if r in {"key", "key_name"}:
        return p.key_name
    if r in {"dim", "comment"}:
        return p.dim
    if r in {"name", "value_name"}:
        return p.value_name
    if r in {"exercise_name", "value_exercise_name"}:
        return p.value_exercise_name
    if r in {"enum", "value_enum", "mode"}:
        return p.value_enum
    if r in {"cadence", "value_cadence"}:
        return p.value_cadence
    if r in {"number", "num", "value_number"}:
        return p.value_number
    if r in {"true", "bool_true"}:
        return p.bool_true
    if r in {"false", "bool_false"}:
        return p.bool_false
    if r in {"null"}:
        return p.null or p.dim

    # allow direct palette field name
    if hasattr(p, r):
        v = getattr(p, r)
        return v if isinstance(v, str) else None

    return None


def _style_text(s: str, theme: ThemeSpec, *, role: str | None) -> Text:
    base = _base_style(theme)
    t = Text(s, style=base)
    color = _role_to_color(role, theme)
    if color:
        t.stylize(f"{color} on {theme.palette.bg}", 0, len(s))
    return t


def _style_scalar_value(value: Any, theme: ThemeSpec, *, role: str | None) -> Text:
    # Scalars with typing-aware fallback to palette roles
    if value is None:
        return _style_text("null", theme, role=role or "null")

    if isinstance(value, bool):
        return _style_text("true" if value else "false", theme, role=("true" if value else "false"))

    if isinstance(value, (int, float)):
        return _style_text(str(value), theme, role=role or "number")

    # string / other
    return _style_text(str(value), theme, role=role)


def _format_with_value(fmt: str, value: Any) -> str:
    return fmt.replace("{value}", str(value))


def _apply_value_spec(value: Any, theme: ThemeSpec, value_spec: dict[str, Any] | None) -> Text:
    """
    value_spec supports:
      role: <role>
      brackets: true
      format: " x {value} kg"
    """
    role = None
    brackets = False
    fmt = None

    if isinstance(value_spec, dict):
        role = value_spec.get("role")
        brackets = bool(value_spec.get("brackets", False))
        fmt = value_spec.get("format")

    # string formatting before style
    out_value = value
    if isinstance(fmt, str) and fmt:
        out_value = _format_with_value(fmt, value)
        # formatted output is a string; keep role styling over the whole fragment
        t = _style_text(str(out_value), theme, role=role)
    else:
        t = _style_scalar_value(out_value, theme, role=role)

    if brackets:
        left = _style_text("[", theme, role="plain")
        right = _style_text("]", theme, role="plain")
        return Text.assemble(left, t, right, style=_base_style(theme))

    return t


def _print_human_line(console: Console, theme: ThemeSpec, indent: int, content: Text, *, indent_spaces: int) -> None:
    prefix = " " * (indent_spaces * indent)
    line = Text(prefix, style=_base_style(theme))
    line.append(content)
    _print_full_width(console, line, theme.palette.bg)


def _render_key_value_line(
    console: Console,
    theme: ThemeSpec,
    *,
    key: str,
    value: Any,
    render: dict[str, Any],
    indent: int,
    indent_spaces: int,
) -> None:
    show_label = bool(render.get("show_label", True))
    label = render.get("label")
    if not isinstance(label, str) or not label.strip():
        label = key

    value_spec = render.get("value")
    if value_spec is not None and not isinstance(value_spec, dict):
        value_spec = None

    if show_label:
        key_txt = _style_text(f"{label}: ", theme, role="key")
        key_txt.append_text(_apply_value_spec(value, theme, value_spec))
        _print_human_line(console, theme, indent, key_txt, indent_spaces=indent_spaces)
    else:
        _print_human_line(console, theme, indent, _apply_value_spec(value, theme, value_spec), indent_spaces=indent_spaces)


def _get_dict_value_case_insensitive(d: dict[str, Any], key: str) -> Any:
    want = key.strip().lower()
    for k, v in d.items():
        if _norm_key(k) == want:
            return v
    return None


def _render_exercise_lines(
    console: Console,
    theme: ThemeSpec,
    *,
    exercises: list[Any],
    render: dict[str, Any],
    indent: int,
    indent_spaces: int,
) -> None:
    """
    render:
      template: "{name}{reps}{time}{weight}"
      parts:
        name: {from: name, role: exercise_name}
        reps: {when_exists: reps, format: " x {value}", role: number}
        ...
    """
    template = render.get("template") or "{name}"
    if not isinstance(template, str) or not template.strip():
        template = "{name}"

    parts = render.get("parts") or {}
    if not isinstance(parts, dict):
        parts = {}

    # placeholder order from template
    ph_re = re.compile(r"\{([a-zA-Z0-9_]+)\}")
    placeholders = ph_re.findall(template)
    if not placeholders:
        placeholders = ["name"]

    for ex in exercises:
        # if it's not a dict, just print it scalar
        if not isinstance(ex, dict):
            _print_human_line(console, theme, indent, _style_scalar_value(ex, theme, role="plain"), indent_spaces=indent_spaces)
            continue

        line = Text("", style=_base_style(theme))

        for ph in placeholders:
            ps = parts.get(ph) or {}
            if not isinstance(ps, dict):
                continue

            from_key = ps.get("from", ph)
            when_exists = ps.get("when_exists")
            role = ps.get("role")
            fmt = ps.get("format")

            if when_exists is not None:
                v_check = _get_dict_value_case_insensitive(ex, str(when_exists))
                if v_check is None or str(v_check).strip() == "":
                    continue

            v = _get_dict_value_case_insensitive(ex, str(from_key))
            if v is None or str(v).strip() == "":
                if ph == "name":
                    v = "Exercise"
                else:
                    continue

            fragment_value: Any = v
            if isinstance(fmt, str) and fmt:
                fragment_value = _format_with_value(fmt, v)
                fragment = _style_text(str(fragment_value), theme, role=role)
            else:
                fragment = _style_scalar_value(fragment_value, theme, role=role)

            line.append_text(fragment)

        # optional: show_label flag (default false for exercises)
        show_label = bool(render.get("show_label", False))
        if show_label:
            key_txt = _style_text("EXERCISE: ", theme, role="key")
            key_txt.append_text(line)
            _print_human_line(console, theme, indent, key_txt, indent_spaces=indent_spaces)
        else:
            _print_human_line(console, theme, indent, line, indent_spaces=indent_spaces)


def _render_human_node(
    console: Console,
    theme: ThemeSpec,
    *,
    schema: dict[str, Any],
    rules: list[dict[str, Any]],
    node: Any,
    canonical_path: str,
    indent: int,
    indent_spaces: int,
) -> None:
    """
    Traversal:
      - dict: per key
      - list: items (no '-' in human mode; indentation preserved)
    Rules can match:
      - key-only
      - path-only (usually for containers like exercises)
      - path+key
    """
    # container-level rule (path-only) e.g. exercises special renderer
    if isinstance(node, list):
        # Allow path rules at the list container, i.e. "...exercises[]"
        r_path = _find_rule(rules, canonical_path=canonical_path, key=None)
        if r_path:
            render = r_path.get("render") or {}
            if isinstance(render, dict) and render.get("as") == "exercise_lines":
                _render_exercise_lines(
                    console,
                    theme,
                    exercises=node,
                    render=render,
                    indent=indent,
                    indent_spaces=indent_spaces,
                )
                return

        # default list rendering (no hyphens)
        for item in node:
            if isinstance(item, (dict, list)):
                _render_human_node(
                    console,
                    theme,
                    schema=schema,
                    rules=rules,
                    node=item,
                    canonical_path=canonical_path,
                    indent=indent,
                    indent_spaces=indent_spaces,
                )
            else:
                _print_human_line(
                    console,
                    theme,
                    indent,
                    _style_scalar_value(item, theme, role="plain"),
                    indent_spaces=indent_spaces,
                )
        return

    # scalar root
    if not isinstance(node, dict):
        _print_human_line(
            console,
            theme,
            indent,
            _style_scalar_value(node, theme, role="plain"),
            indent_spaces=indent_spaces,
        )
        return

    # --- PATH RULE for dict nodes (e.g., stages[].jobs[]) ---
    # Only inject header_line and then continue NORMAL dict rendering,
    # skipping the keys already included in the header.
    skip_keys: set[str] = set()
    path_rule = _schema_find_path_rule(schema, canonical_path)
    if path_rule:
        render = path_rule.get("render") or {}
        if isinstance(render, dict) and render.get("as") == "header_line":
            if render.get("blank_before"):
                _print_full_width(console, Text("", style=_base_style(theme)), theme.palette.bg)

            # MUST return the source keys used by the header (e.g. {"name","mode"} normalized)
            skip_keys = _render_header_line(
                console,
                theme,
                indent=indent,
                node=node,
                render=render,
            )

    # NORMAL dict rendering (unchanged), with a single skip at the top
    for k, v in node.items():
        k_lower = _norm_key(k)
        if skip_keys and k_lower in skip_keys:
            continue

        key = str(k)
        key_path = _to_canonical_path_for_key(canonical_path, k_lower)

        # if this key is a list, we create container path "...key[]"
        if isinstance(v, list):
            list_path = _to_canonical_path_for_list(canonical_path, k_lower)

            r_key = _find_rule(rules, canonical_path=key_path, key=k_lower)
            if r_key:
                render = r_key.get("render") or {}
                if isinstance(render, dict) and render.get("show_label") is False and render.get("value") is not None:
                    _render_human_node(
                        console,
                        theme,
                        schema=schema,
                        rules=rules,
                        node=v,
                        canonical_path=list_path,
                        indent=indent,
                        indent_spaces=indent_spaces,
                    )
                    continue

            r_path = _find_rule(rules, canonical_path=list_path, key=None)
            if r_path:
                render = r_path.get("render") or {}
                if isinstance(render, dict) and render.get("as") == "exercise_lines":
                    _render_exercise_lines(
                        console,
                        theme,
                        exercises=v,
                        render=render,
                        indent=indent,
                        indent_spaces=indent_spaces,
                    )
                    continue

            if r_key:
                render = r_key.get("render") or {}
                if isinstance(render, dict) and render.get("show_label") is False:
                    _render_human_node(
                        console,
                        theme,
                        schema=schema,
                        rules=rules,
                        node=v,
                        canonical_path=list_path,
                        indent=indent,
                        indent_spaces=indent_spaces,
                    )
                else:
                    label = (render.get("label") if isinstance(render, dict) else None) or key
                    _print_human_line(
                        console,
                        theme,
                        indent,
                        _style_text(f"{label}:", theme, role="key"),
                        indent_spaces=indent_spaces,
                    )
                    _render_human_node(
                        console,
                        theme,
                        schema=schema,
                        rules=rules,
                        node=v,
                        canonical_path=list_path,
                        indent=indent + 1,
                        indent_spaces=indent_spaces,
                    )
            else:
                _print_human_line(
                    console,
                    theme,
                    indent,
                    _style_text(f"{key}:", theme, role="key"),
                    indent_spaces=indent_spaces,
                )
                _render_human_node(
                    console,
                    theme,
                    schema=schema,
                    rules=rules,
                    node=v,
                    canonical_path=list_path,
                    indent=indent + 1,
                    indent_spaces=indent_spaces,
                )
            continue

        # dict child
        if isinstance(v, dict):
            r_key = _find_rule(rules, canonical_path=key_path, key=k_lower)
            if r_key:
                render = r_key.get("render") or {}
                if isinstance(render, dict) and render.get("show_label") is False:
                    _render_human_node(
                        console,
                        theme,
                        schema=schema,
                        rules=rules,
                        node=v,
                        canonical_path=key_path,
                        indent=indent,
                        indent_spaces=indent_spaces,
                    )
                else:
                    label = (render.get("label") if isinstance(render, dict) else None) or key
                    _print_human_line(
                        console,
                        theme,
                        indent,
                        _style_text(f"{label}:", theme, role="key"),
                        indent_spaces=indent_spaces,
                    )
                    _render_human_node(
                        console,
                        theme,
                        schema=schema,
                        rules=rules,
                        node=v,
                        canonical_path=key_path,
                        indent=indent + 1,
                        indent_spaces=indent_spaces,
                    )
            else:
                _print_human_line(
                    console,
                    theme,
                    indent,
                    _style_text(f"{key}:", theme, role="key"),
                    indent_spaces=indent_spaces,
                )
                _render_human_node(
                    console,
                    theme,
                    schema=schema,
                    rules=rules,
                    node=v,
                    canonical_path=key_path,
                    indent=indent + 1,
                    indent_spaces=indent_spaces,
                )
            continue

        # scalar field
        r_key = _find_rule(rules, canonical_path=key_path, key=k_lower)
        if r_key:
            render = r_key.get("render") or {}
            if isinstance(render, dict):
                _render_key_value_line(
                    console,
                    theme,
                    key=key,
                    value=v,
                    render=render,
                    indent=indent,
                    indent_spaces=indent_spaces,
                )
                continue

        # default scalar printing: KEY: value
        key_txt = _style_text(f"{key}: ", theme, role="key")
        key_txt.append_text(_style_scalar_value(v, theme, role="plain"))
        _print_human_line(console, theme, indent, key_txt, indent_spaces=indent_spaces)

# =============================================================================
# Render schema helpers (required by --human)
# =============================================================================

def _schema_load_yaml(text: str) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception:
        raise SystemExit("Missing dependency: PyYAML. Install with: pip install pyyaml")

    try:
        data = yaml.safe_load(text) or {}
    except Exception as e:
        raise SystemExit(f"Render schema YAML parse failed: {e}")

    if not isinstance(data, dict):
        raise SystemExit("Render schema must be a YAML mapping (dict).")

    return data

_PATH_INDEX_RE = re.compile(r"\[\d+\]")

def _norm_path(path: str) -> str:
    # stages[0].jobs[2] -> stages[].jobs[]
    return _PATH_INDEX_RE.sub("[]", path)

def _node_get(node: Any, key: str) -> Any:
    """Case-insensitive-ish lookup for YAML keys that might be NAME/MODE/etc."""
    if not isinstance(node, dict):
        return None
    if key in node:
        return node[key]
    # common casings
    up = key.upper()
    if up in node:
        return node[up]
    cap = key.capitalize()
    if cap in node:
        return node[cap]
    # last resort: scan (avoid heavy logic)
    kl = key.lower()
    for k, v in node.items():
        if isinstance(k, str) and k.strip().lower() == kl:
            return v
    return None

def _schema_find_path_rule(schema: dict[str, Any], canonical_path: str) -> dict[str, Any] | None:
    rules = _schema_rules(schema)
    want = _norm_path(canonical_path)
    for r in rules:
        m = r.get("match") or {}
        if not isinstance(m, dict):
            continue
        rp = m.get("path")
        if isinstance(rp, str) and rp.strip() == want:
            return r
    return None

_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")


def _schema_get_defaults(schema: dict[str, Any]) -> dict[str, Any]:
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
def _style_for_role(theme: ThemeSpec, role: str) -> str:
    """Translate a render-schema role to a Rich style string."""
    p = theme.palette
    bg = p.bg

    role = (role or "plain").strip().lower()

    if role == "enum":
        return f"{p.value_enum} on {bg}"
    if role == "name":
        return f"{p.value_name} on {bg}"
    if role == "exercise_name":
        return f"{p.value_exercise_name} on {bg}"
    if role == "number":
        return f"{p.value_number} on {bg}"
    if role == "cadence":
        return f"{getattr(p, 'value_cadence', p.plain_fg or p.dim)} on {bg}"
    if role == "key":
        return f"{p.key_name} on {bg}"
    if role == "dim":
        return f"{p.dim} on {bg}"

    # plain / fallback
    return _base_style(theme)


def _render_header_line(
    console: Console,
    theme: ThemeSpec,
    indent: int,
    node: dict[str, Any],
    render: dict[str, Any],
) -> set[str]:
    """
    Prints a composed header line and returns the set of source keys used,
    so caller can skip rendering them again.
    """
    p = theme.palette

    template = str(render.get("template") or "")
    parts = render.get("parts") or {}
    if not isinstance(parts, dict):
        parts = {}

    # NEW: line-level styles
    line_role = str(render.get("line_role") or "plain")
    literal_role = str(render.get("literal_role") or line_role)
    default_part_role = str(render.get("default_part_role") or line_role)

    base_style = _style_for_role(theme, line_role)
    lit_style = _style_for_role(theme, literal_role)

    used_src_keys: set[str] = set()

    out = Text(style=base_style)

    pos = 0
    for m in _PLACEHOLDER_RE.finditer(template):
        # literal chunk
        lit = template[pos:m.start()]
        if lit:
            out.append(lit, style=lit_style)

        name = m.group(1)
        spec = parts.get(name) or {}
        if not isinstance(spec, dict):
            spec = {}

        src_key = str(spec.get("from") or name)
        used_src_keys.add(_norm_key(src_key))

        raw_val = _node_get(node, src_key)
        val = "" if raw_val is None else str(raw_val)

        # map
        mp = spec.get("map")
        if isinstance(mp, dict):
            val = str(mp.get(val, mp.get(val.lower(), val)))

        # transforms
        transforms = spec.get("transform") or []
        if isinstance(transforms, list):
            for t in transforms:
                if t == "upper":
                    val = val.upper()
                elif t == "lower":
                    val = val.lower()
                elif t == "snake_to_label":
                    val = val.replace("_", " ")

        role = str(spec.get("role") or default_part_role)
        out.append(val, style=_style_for_role(theme, role))
        pos = m.end()

    # trailing literal
    tail = template[pos:]
    if tail:
        out.append(tail, style=lit_style)

    # indent
    if indent > 0:
        out = Text(" " * indent, style=base_style) + out

    _print_full_width(console, out, p.bg)
    return used_src_keys

def _schema_rules(schema: dict[str, Any]) -> list[dict[str, Any]]:
    rules = schema.get("rules") or []
    if not isinstance(rules, list):
        raise SystemExit("render schema 'rules' must be a list.")
    return [r for r in rules if isinstance(r, dict)]

def preview_human_text(text: str, theme: ThemeSpec, schema_text: str | None, schema_source: str) -> None:
    console = build_console()
    p = theme.palette

    try:
        import yaml  # type: ignore
    except Exception:
        raise SystemExit("Missing dependency: PyYAML. Install with: pip install pyyaml")

    try:
        data = yaml.safe_load(text)
    except Exception as e:
        raise SystemExit(f"YAML parse failed (needed for --human): {e}")

    schema_raw = schema_text if schema_text is not None else DEFAULT_RENDER_SCHEMA_YAML
    schema = _schema_load_yaml(schema_raw)
    defaults = _schema_get_defaults(schema)
    indent_spaces = int(defaults.get("indent_spaces", 2))
    rules = _schema_rules(schema)

    # Header
    console.print(Rule(style=p.bg_alt))
    header = Text(style=_base_style(theme))
    header.append(" RawTrainer YAML Human Preview ", style=f"{p.key_name} on {p.bg}")
    header.append(f"— {theme.name} ", style=f"{p.value_enum} on {p.bg}")
    header.append(f"  Schema: {schema_source} ", style=f"{p.dim} on {p.bg}")
    _print_full_width(console, header, p.bg)
    console.print(Rule(style=p.bg_alt))

    _render_human_node(
        console,
        theme,
        schema=schema,
        rules=rules,
        node=data,
        canonical_path="",
        indent=0,
        indent_spaces=indent_spaces,
    )

    console.print(Rule(style=p.bg_alt))
    console.print()


# =============================================================================
# CLI
# =============================================================================

def main() -> int:
    ap = argparse.ArgumentParser(description="Preview YAML with multiple RawTrainer themes.")
    ap.add_argument("yaml_file", type=Path, help="Path to YAML file")
    ap.add_argument("--theme", action="append", help="Theme name to render (repeatable). Defaults to all.")
    ap.add_argument("--list-themes", action="store_true", help="List available themes and exit.")
    ap.add_argument(
        "--human",
        action="store_true",
        help="Human-friendly print using a YAML render schema.",
    )
    ap.add_argument(
        "--render-schema",
        type=Path,
        help="Path to render schema YAML (used only with --human). If omitted, uses built-in default.",
    )
    ap.add_argument(
        "--dump-default-render-schema",
        action="store_true",
        help="Print the built-in default render schema YAML and exit.",
    )
    args = ap.parse_args()

    if args.dump_default_render_schema:
        print(DEFAULT_RENDER_SCHEMA_YAML.rstrip())
        return 0

    if args.list_themes:
        print("Available themes:")
        for name in THEMES:
            print(f" - {name}")
        return 0

    if not args.yaml_file.exists():
        raise SystemExit(f"File not found: {args.yaml_file}")

    text = args.yaml_file.read_text(encoding="utf-8", errors="replace")

    schema_text: str | None = None
    schema_source = "DEFAULT"

    if args.human and args.render_schema:
        if not args.render_schema.exists():
            raise SystemExit(f"Render schema not found: {args.render_schema}")
        schema_text = args.render_schema.read_text(encoding="utf-8", errors="replace")
        schema_source = str(args.render_schema.resolve())

    selected = args.theme or list(THEMES.keys())
    for name in selected:
        if name not in THEMES:
            raise SystemExit(f"Unknown theme: {name}. Use --list-themes.")
        theme = THEMES[name]

        if args.human:
            preview_human_text(text, theme, schema_text, schema_source)
        else:
            preview_yaml_text(text, theme)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())