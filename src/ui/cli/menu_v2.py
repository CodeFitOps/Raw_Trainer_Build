# src/ui/cli/menu_v2.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Iterable

from src.ui.cli.style import title, info, error, prompt

log = logging.getLogger(__name__)

RunV2Fn = Callable[[Path], int]
PreviewV2Fn = Callable[[Path], int]


def _candidate_dirs() -> list[Path]:
    home = Path.home()
    return [
        #home / "Documents",
        #home / "Downloads",
        Path("data/workouts_files"),
        #Path("internal_tools/examples"),
    ]


def _discover_yaml_files() -> list[Path]:
    files: list[Path] = []
    for d in _candidate_dirs():
        try:
            if d.is_dir():
                files.extend(sorted(d.glob("*.yml")))
                files.extend(sorted(d.glob("*.yaml")))
        except OSError:
            continue

    # unique + existing
    uniq = []
    seen = set()
    for p in files:
        try:
            rp = p.resolve()
        except Exception:
            rp = p
        if str(rp) in seen:
            continue
        seen.add(str(rp))
        if p.is_file():
            uniq.append(p)
    return uniq


def _select_yaml_from_common_locations() -> Path | None:
    files = _discover_yaml_files()
    if not files:
        print(info("\nNo YAML workouts found in common folders."))
        return None

    print("\nDetected YAML workouts in common folders:")
    for idx, p in enumerate(files, start=1):
        print(f"  {idx}) {p}")
    print("  0) Enter custom path")
    print("  c) Cancel")

    while True:
        raw = input(prompt("Choose file number or enter path (or 'c' to cancel): ")).strip()
        if raw.lower() in {"c", "q"}:
            return None
        if raw == "0":
            path_str = input(prompt("Enter full path: ")).strip()
            if not path_str:
                return None
            p = Path(path_str).expanduser()
            return p if p.is_file() else None

        if raw.isdigit():
            i = int(raw)
            if 1 <= i <= len(files):
                return files[i - 1]
            print(error("Invalid selection. Out of range."))
            continue

        # allow direct path typing
        p = Path(raw).expanduser()
        if p.is_file():
            return p

        print(error("Invalid input. Enter a number or a valid file path."))


def menu_loop_v2(preview_v2_fn: PreviewV2Fn, run_v2_fn: RunV2Fn) -> int:
    """
    Menú interactivo v2 (JSON Schemas + domain_v2).

    - preview_v2_fn(path) -> exit code
    - run_v2_fn(path) -> exit code
    """
    while True:
        print(title("\n===================================="))
        print(title("***                                "))
        print(title(" <_ RawTrainer CLI"))
        #print(title("===================================="))
        #print(title("========================Engineered== "))
        print(title("=======================CodeEngTools="))
        print()
        print(title("[1] Preview Workout (v2)"))
        print(title("[2] Run Workout (v2 manual)"))
        print(title("[3] Exit"))

        choice = input(prompt("> ")).strip()

        if choice == "1":
            path = _select_yaml_from_common_locations()
            if not path:
                continue
            code = preview_v2_fn(path)
            log.debug("preview-v2 finished with exit code %d", code)

        elif choice == "2":
            path = _select_yaml_from_common_locations()
            if not path:
                continue
            code = run_v2_fn(path)
            log.debug("run-v2 finished with exit code %d", code)

        elif choice == "3":
            print(info("Bye!"))
            return 0

        else:
            print(error("Invalid option. Please choose 1, 2 or 3."))