#!/usr/bin/env python
"""
Generate shell alias suggestions for RawTrainer CLI.

Usage (from project root):

    python internal_tools/generate_shell_aliases.py
    python internal_tools/generate_shell_aliases.py --workouts-dir internal_tools/examples

It prints a block of shell code (zsh/bash compatible) that you can paste into
your ~/.zshrc or ~/.bashrc.
"""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None


def slug_from_filename(path: Path) -> str:
    """
    Convert 'custom_sets_tabata.yaml' -> 'custom_sets_tabata'
    and sanitize a bit for alias names.
    """
    name = path.stem  # remove .yaml
    # very simple sanitize: lowercase, replace spaces and dashes by underscore
    slug = name.lower().replace(" ", "_").replace("-", "_")
    return slug


def build_description_comment(file_path: Path) -> str:
    """
    Read the YAML file (if PyYAML is available) and build a short
    ' # NAME — Description' comment string.

    If anything falla (no yaml, parse error, missing fields),
    returns '' (no comment).
    """
    if yaml is None:
        return ""

    try:
        text = file_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
    except Exception:
        return ""

    if not isinstance(data, dict):
        return ""

    name = data.get("NAME") or data.get("name")
    desc = data.get("Description") or data.get("description")

    parts: list[str] = []
    if isinstance(name, str) and name.strip():
        parts.append(name.strip())
    if isinstance(desc, str) and desc.strip():
        parts.append(desc.strip())

    if not parts:
        return ""

    return "  # " + " — ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate RawTrainer shell aliases from workout YAML files."
    )
    parser.add_argument(
        "--workouts-dir",
        type=Path,
        default=Path("internal_tools") / "examples",
        help="Directory where workout YAML files live (default: internal_tools/examples)",
    )
    if isinstance(name, str) and name.strip():
        parts.append(name.strip())
    if isinstance(desc, str) and desc.strip():
        parts.append(desc.strip())

    if not parts:
        return ""

    return "  # " + " — ".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate RawTrainer shell aliases from workout YAML files."
    )
    parser.add_argument(
        "--workouts-dir",
        type=Path,
        default=Path("data") / "workouts_files",
        help="Directory where workout YAML files live (default: data/workouts_files)",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    workouts_dir = (project_root / args.workouts_dir).resolve()

    if not workouts_dir.is_dir():
        raise SystemExit(f"ERROR: workouts directory not found: {workouts_dir}")

    # Collect *.yaml workouts (non-recursive for now; switch to rglob if you want subdirs)
    from itertools import chain
    workout_files = sorted(
        chain(
            workouts_dir.glob("*.yaml"),
            workouts_dir.glob("*.yml"),
        )
    )
    if not workout_files:
        raise SystemExit(f"No .yaml workouts found in {workouts_dir}")

    # Build relative paths from project root (para que encajen con rt alias)
    rel_paths = [wf.relative_to(project_root) for wf in workout_files]

    # --- Print header ---
    print("# --- RawTrainer environment helper ---")
    print("rawenv() {")
    print("  cd ~/repos/Raw_Trainer_Build || return")
    print("  if [[ -d .venv ]]; then")
    print("    source .venv/bin/activate")
    print("  fi")
    print("}")
    print()
    print("# --- RawTrainer CLI shortcuts ---")
    print("alias rt='rawenv && python main.py'")
    print("alias rtv='rt validate'")
    print("alias rtp='rt preview'")
    print()
    print("# --- Auto-generated workout aliases (preview & validate) ---")

    for wf, rel_path in zip(workout_files, rel_paths):
        slug = slug_from_filename(rel_path)
        comment = build_description_comment(wf)

        # ejemplo: rtp_custom_sets_tabata, rtv_custom_sets_tabata
        print(
            f"alias rtp_{slug}='rt preview {rel_path.as_posix()}'{comment}"
        )
        print(
            f"alias rtv_{slug}='rt validate {rel_path.as_posix()}'{comment}"
        )

    print()
    print("# Copy/paste this block into your ~/.zshrc or ~/.bashrc.")
    print("# After that, reload your shell:  source ~/.zshrc")


if __name__ == "__main__":
    raise SystemExit(main())