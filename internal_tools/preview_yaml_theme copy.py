#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path


# Optional: make running as a script reliable (python internal_tools/preview_yaml_theme.py ...)
# When running as a module (-m), this is harmless.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


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


def main(argv: list[str] | None = None) -> int:
    # Import here to avoid partial-module states / NameError if something changes during refactor
    from rawtrainer_prettyprint.renderer import (
        preview_yaml_text,
        preview_human_text,
        preview_human_stepwise,
    )
    from rawtrainer_prettyprint.themes import THEMES

    ap = argparse.ArgumentParser(description="Preview YAML with RawTrainer themes.")
    ap.add_argument("yaml_file", type=Path, help="Path to YAML file")
    ap.add_argument("--theme", action="append", help="Theme name to render (repeatable). Defaults to all.")
    ap.add_argument("--list-themes", action="store_true", help="List available themes and exit.")
    ap.add_argument("--human", action="store_true", help="Human-friendly print using a YAML render schema.")
    ap.add_argument("--step", action="store_true", help="Human mode: print one job at a time and wait for input.")
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
    args = ap.parse_args(argv)

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
    schema_source = "DEFAULT_RENDER_SCHEMA_YAML"

    if args.human:
        if args.render_schema:
            if not args.render_schema.exists():
                raise SystemExit(f"Render schema not found: {args.render_schema}")
            schema_text = args.render_schema.read_text(encoding="utf-8", errors="replace")
            schema_source = str(args.render_schema.resolve())
        else:
            schema_text = DEFAULT_RENDER_SCHEMA_YAML

    selected = args.theme or list(THEMES.keys())
    for name in selected:
        if name not in THEMES:
            raise SystemExit(f"Unknown theme: {name}. Use --list-themes.")
        theme = THEMES[name]

        if args.human:
            if args.step:
                preview_human_stepwise(text, theme, schema_text, schema_source)
            else:
                preview_human_text(text, theme, schema_text, schema_source)
        else:
            preview_yaml_text(text, theme)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())