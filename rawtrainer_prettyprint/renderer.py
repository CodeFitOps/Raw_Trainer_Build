#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Any

from rich.console import Console
from rich.rule import Rule
from rich.text import Text
from .themes import _lower_set
from .themes import ThemeSpec
from .schema import (
    load_render_schema,
    find_path_rule,
    find_rule,
    render_defaults,   # <-- ADD
    _schema_rules_only,
    render_rules,

)
from .ci_strict import ci_get_str, ci_get_list 
import re

KEY_RE = re.compile(
    r"^(\s*-\s*)?(\s*)(?P<key>(?:'[^']*'|\"[^\"]*\"|[^:#\n]+?))(\s*:)"
)
NUM_RE = re.compile(r"\b\d+\b")
BOOL_NULL_RE = re.compile(r"\b(true|false|null)\b", re.IGNORECASE)
BLOCK_SCALAR_RE = re.compile(r"^(?:[>|])(?:[+-])?$")
_PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z0-9_]+)\}")

def _norm_key(x: Any) -> str:
    return str(x).strip().lower()

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

def _use_bg(theme: ThemeSpec) -> bool:
    """
    If True, we paint an explicit background color (banded look).
    If False, we let the terminal background show through.
    """
    r = theme.rules
    # Reuse existing flag to avoid touching ThemeSpec/Rules model:
    # If terminal fg is used, we *should not* force any background.
    return not bool(getattr(r, "use_terminal_fg", False))

def _base_style(theme: ThemeSpec) -> str:
    p = theme.palette
    r = theme.rules

    # If we want terminal background, don't force any bg.
    if not _use_bg(theme):
        # If we rely on terminal foreground too, return empty style.
        if r.use_terminal_fg:
            return ""
        return f"{p.plain_fg}"

    # Explicit background mode (current look)
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


def _print_full_width(console: Console, text: Text, bg: str, theme: ThemeSpec | None = None) -> None:
    """
    In background mode, pad the line to full width using background color.
    In terminal-bg mode, do not pad with background; let terminal bg show.
    """
    if theme is not None and not _use_bg(theme):
        console.print(text, highlight=False, no_wrap=True, overflow="crop")
        return

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

def _canonical_path_join(base: str, seg: str) -> str:
    return seg if not base else f"{base}.{seg}"

def _to_canonical_path_for_key(parent_path: str, key: str) -> str:
    return _canonical_path_join(parent_path, key)

def _to_canonical_path_for_list(parent_path: str, list_key: str) -> str:
    return _canonical_path_join(parent_path, f"{list_key}[]")

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
        return getattr(p, "value_cadence", None) or (p.plain_fg if p.plain_fg else p.dim)
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
      item_prefix: "- "            # NEW (optional)
      item_prefix_role: "dim"      # NEW (optional)
    """
    template = render.get("template") or "{name}"
    if not isinstance(template, str) or not template.strip():
        template = "{name}"

    parts = render.get("parts") or {}
    if not isinstance(parts, dict):
        parts = {}

    # NEW: item prefix (bullet)
    item_prefix = render.get("item_prefix", "- ")
    if not isinstance(item_prefix, str):
        item_prefix = "- "
    item_prefix_role = render.get("item_prefix_role", "dim")
    if not isinstance(item_prefix_role, str) or not item_prefix_role.strip():
        item_prefix_role = "dim"

    # placeholder order from template
    ph_re = re.compile(r"\{([a-zA-Z0-9_]+)\}")
    placeholders = ph_re.findall(template)
    if not placeholders:
        placeholders = ["name"]

    for ex in exercises:
        # Prefix text per line
        prefix_txt = Text("", style=_base_style(theme))
        if item_prefix:
            prefix_txt = _style_text(item_prefix, theme, role=item_prefix_role)

        # if it's not a dict, just print it scalar (with prefix)
        if not isinstance(ex, dict):
            val_txt = _style_scalar_value(ex, theme, role="plain")
            out_line = Text("", style=_base_style(theme))
            out_line.append_text(prefix_txt)
            out_line.append_text(val_txt)
            _print_human_line(console, theme, indent, out_line, indent_spaces=indent_spaces)
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

        # apply prefix to the final printed line
        out_line = Text("", style=_base_style(theme))
        out_line.append_text(prefix_txt)
        out_line.append_text(line)

        # optional: show_label flag (default false for exercises)
        show_label = bool(render.get("show_label", False))
        if show_label:
            key_txt = _style_text("EXERCISE: ", theme, role="key")
            key_txt.append_text(out_line)
            _print_human_line(console, theme, indent, key_txt, indent_spaces=indent_spaces)
        else:
            _print_human_line(console, theme, indent, out_line, indent_spaces=indent_spaces)

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
        r_path = find_rule(rules, canonical_path=canonical_path, key=None)
        if r_path:
            render = r_path.get("render") or {}
            if isinstance(render, dict) and render.get("as") == "exercise_lines":
                _render_exercise_lines(
                    console,
                    theme,
                    exercises=node,
                    render=render,
                    indent=indent + 1,
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
    path_rule = find_path_rule(schema, canonical_path)
    if path_rule:
        render = path_rule.get("render") or {}
        if isinstance(render, dict) and render.get("as") == "header_line":
            if render.get("blank_before"):
                _print_full_width(console, Text("", style=_base_style(theme)), theme.palette.bg, theme=theme)

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

            r_key = render_rules(rules, canonical_path=key_path, key=k_lower)
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

            r_path = find_rule(rules, canonical_path=list_path, key=None)
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
            r_key = render_rules(rules, canonical_path=key_path, key=k_lower)
            r_key (rules, canonical_path=key_path, key=k_lower)
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
        r_key = render_rules(rules, canonical_path=key_path, key=k_lower)
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

def _node_get(node: Any, key: str) -> Any:
    """Case-insensitive dict getter; returns None if not found."""
    if not isinstance(node, dict):
        return None
    key_l = str(key).strip().lower()
    for k, v in node.items():
        if isinstance(k, str) and k.strip().lower() == key_l:
            return v
    return None

def _render_header_line(
    console: Console,
    theme: ThemeSpec,
    indent: int,
    node: dict[str, Any],
    render: dict[str, Any],
) -> set[str]:
    """
    Prints a composed header block (supports multi-line templates) and returns
    the set of source keys used, so caller can skip rendering them again.

    Supports per-part option:
      wrap: true -> apply the part role style to ALL literals on that line (before/after placeholders)
    """
    p = theme.palette

    template = str(render.get("template") or "")
    parts = render.get("parts") or {}
    if not isinstance(parts, dict):
        parts = {}

    used_src_keys: set[str] = set()

    def _role_style(role: str) -> str:
        role = (role or "plain").strip().lower()
        if role == "enum":
            return f"{p.value_enum} on {p.bg}"
        if role == "name":
            return f"{p.value_name} on {p.bg}"
        if role == "exercise_name":
            return f"{p.value_exercise_name} on {p.bg}"
        if role == "number":
            return f"{p.value_number} on {p.bg}"
        if role == "cadence":
            return f"{getattr(p, 'value_cadence', p.plain_fg or p.dim)} on {p.bg}"
        return _base_style(theme)

    # Split into lines so indent applies to each line
    lines = template.split("\n") if template else [""]

    for tpl_line in lines:
        # ✅ Pre-scan: if any placeholder has wrap:true, use its role style for ALL literals in the line
        literal_style: str | None = None
        for m0 in _PLACEHOLDER_RE.finditer(tpl_line):
            ph0 = m0.group(1)
            spec0 = parts.get(ph0) or {}
            if not isinstance(spec0, dict):
                continue
            if spec0.get("wrap") is True:
                literal_style = _role_style(str(spec0.get("role") or "plain"))
                break

        base_line_style = literal_style or _base_style(theme)
        out = Text(style=base_line_style)

        pos = 0
        for m in _PLACEHOLDER_RE.finditer(tpl_line):
            # literal chunk
            lit = tpl_line[pos:m.start()]
            if lit:
                out.append(lit, style=base_line_style)

            name = m.group(1)
            spec = parts.get(name) or {}
            if not isinstance(spec, dict):
                spec = {}

            src_key = str(spec.get("from") or name)
            used_src_keys.add(src_key.lower())

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

            role = str(spec.get("role") or "plain")
            style = _role_style(role)

            out.append(val, style=style)
            pos = m.end()

        # trailing literal
        tail = tpl_line[pos:]
        if tail:
            out.append(tail, style=base_line_style)

        # indent
        if indent > 0:
            out = Text(" " * indent) + out

        _print_full_width(console, out, p.bg, theme=theme)

    return used_src_keys

def _prompt_continue() -> bool:
    try:
        ans = input("[Enter] next job | [q] quit: ").strip().casefold()
    except (EOFError, KeyboardInterrupt):
        # If stdin is not interactive, don't hard-fail: just stop stepwise.
        return False

    if ans in ("q", "quit"):
        return False

    # Empty input (Enter) means continue
    return True

def _fg_style(theme: ThemeSpec, fg: str) -> str:
    p = theme.palette
    if _use_bg(theme):
        return f"{fg} on {p.bg}"
    return f"{fg}"

def preview_human_stepwise(
    text: str,
    theme: ThemeSpec,
    schema_text: str | None,
    schema_source: str,
) -> None:
    console = build_console()
    p = theme.palette

    # Load YAML workout
    try:
        import yaml  # type: ignore
    except Exception as e:
        raise SystemExit(f"PyYAML is required for --human mode. Error: {e}")

    workout = yaml.safe_load(text)

    # Load schema
    schema = load_render_schema(schema_text) if schema_text else {}

    # Defaults (indentation, etc.)
    defaults = render_defaults(schema) if isinstance(schema, dict) else {}
    indent_spaces = int(defaults.get("indent_spaces", 2))

    # Rules (ensure list[dict])
    rules = _schema_rules_only(schema) if isinstance(schema, dict) else []
    if not isinstance(rules, list):
        rules = []
    rules = [r for r in rules if isinstance(r, dict)]

    # Header once

    console.print(Rule(style=p.bg_alt))
    header = Text(style=_base_style(theme))
    header.append(" RawTrainer YAML Human Preview (step) ", style=f"{p.key_name} on {p.bg}")
    header.append(f"— {theme.name} ", style=f"{p.value_enum} on {p.bg}")
    header.append(f"  Schema: {schema_source} ", style=f"{p.dim} on {p.bg}")
    _print_full_width(console, header, p.bg)
    console.print(Rule(style=p.bg_alt))

    # Collect jobs safely
    stages = ci_get_list(workout, "stages", "$")
    if not isinstance(stages, list):
        stages = []

    job_blocks: list[tuple[str, dict[str, Any]]] = []
    for si, st in enumerate(stages):
        if not isinstance(st, dict):
            continue
        jobs = ci_get_list(st, "jobs", f"$.stages[{si}]")
        if not isinstance(jobs, list):
            continue

        stage_name = ci_get_str(st, "name", f"$.stages[{si}]", default=f"Stage {si+1}")
        for ji, jb in enumerate(jobs):
            if not isinstance(jb, dict):
                continue
            job_blocks.append((str(stage_name), jb))

    if not job_blocks:
        # fallback: just render whole thing
        _render_human_node(
            console,
            theme,
            schema=schema,
            rules=rules,
            node=workout,
            canonical_path="",
            indent=0,
            indent_spaces=indent_spaces,
        )
        return

    # Print each job as its own mini-workout to reuse your existing path rules
    for idx, (stage_name, job) in enumerate(job_blocks, start=1):
        # separator
        console.print()
        sep = Text(style=_base_style(theme))
        sep.append(f" Stage: {stage_name} ", style=f"{p.key_name} on {p.bg}")
        sep.append(f" Job {idx}/{len(job_blocks)} ", style=f"{p.dim} on {p.bg}")
        _print_full_width(console, sep, p.bg)
        console.print(Rule(style=p.bg_alt))

        # Render ONLY this job, but wrap it in the same structure so the path
        # "stages[].jobs[]" still matches and your header_line rule fires.
        mini = {"stages": [{"name": stage_name, "jobs": [job]}]}

        _render_human_node(
            console,
            theme,
            schema=schema,
            rules=rules,
            node=job,
            canonical_path="stages[].jobs[]",
            indent=indent_spaces,  # 👈 para que cuelgue visualmente del "Stage: ... Job ..."
            indent_spaces=indent_spaces,
        )

        console.print(Rule(style=p.bg_alt))

        if idx < len(job_blocks):
            if not _prompt_continue():
                break

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

    # Load schema
    schema = load_render_schema(schema_text) if schema_text else {}

    # Defaults (indentation, etc.) — ALWAYS define defaults
    defaults: dict[str, Any] = {}
    if isinstance(schema, dict):
        defaults = render_defaults(schema) or {}

    indent_spaces = int(defaults.get("indent_spaces", 2))

    # Rules (ensure list[dict])
    rules = _schema_rules_only(schema) if isinstance(schema, dict) else []
    if not isinstance(rules, list):
        rules = []
    rules = [r for r in rules if isinstance(r, dict)]

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
