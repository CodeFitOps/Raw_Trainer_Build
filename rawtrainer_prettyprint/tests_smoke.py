# rawtrainer_prettyprint/tests_smoke.py
from __future__ import annotations

from pathlib import Path
from typing import Any

from rawtrainer_prettyprint.themes import THEMES
from rawtrainer_prettyprint.renderer import preview_human_text
from rawtrainer_prettyprint.schema import load_default_render_schema_text


def run_one(yaml_path: str, theme_name: str = "raw_yamltools_blue") -> None:
    text = Path(yaml_path).read_text(encoding="utf-8")
    theme = THEMES[theme_name]
    schema_text = load_default_render_schema_text()
    preview_human_text(text, theme, schema_text, "default")


def main() -> None:
    # Ajusta/añade aquí los YAML que siempre quieras validar
    run_one("data/workouts_files/allmodesupdated.yaml", "raw_yamltools_blue")
    run_one("data/workouts_files/upper_A_Planche-HSPU.yaml", "base_synth_purple")


if __name__ == "__main__":
    main()