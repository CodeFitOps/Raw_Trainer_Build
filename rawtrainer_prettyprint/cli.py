from __future__ import annotations

import argparse
from pathlib import Path

from rawtrainer_prettyprint.renderer import (
    preview_yaml_text,
    preview_human_text,
    preview_human_stepwise,
)
from rawtrainer_prettyprint.themes import THEMES

from importlib.resources import files

from rawtrainer_prettyprint.schema import load_render_schema_text, load_default_render_schema_text

def _default_schema_text() -> str:
    return (files("rawtrainer_prettyprint.resources") / "render_schema.yaml").read_text(encoding="utf-8")

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="RawTrainer pretty printer (YAML + human mode).")

    # ✅ yaml_file es opcional para permitir flags como --list-themes / --dump-default-render-schema
    ap.add_argument("yaml_file", type=Path, nargs="?", help="Path to YAML file")

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

    # ✅ comandos que NO requieren yaml_file
    if args.dump_default_render_schema:
        print(load_default_render_schema_text().rstrip())
        return 0

    if args.list_themes:
        print("Available themes:")
        for name in THEMES:
            print(f" - {name}")
        return 0

    # ⛔ a partir de aquí yaml_file es obligatorio
    if args.yaml_file is None:
        ap.error("yaml_file is required unless you use --list-themes or --dump-default-render-schema")

    if not args.yaml_file.exists():
        raise SystemExit(f"File not found: {args.yaml_file}")

    text = args.yaml_file.read_text(encoding="utf-8", errors="replace")

    # Resolve schema only if human mode is enabled
    schema_text: str | None = None
    schema_source = "N/A"
    if args.human:
        schema_text, schema_source = load_render_schema_text(args.render_schema)

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