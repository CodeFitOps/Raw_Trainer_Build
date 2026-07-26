# src/ui/cli/menu.py
"""Enriched terminal menu: the RawTrainer hub.

Thin skin over the application layer (library, components) and the main_cli
handlers — the same a future GUI would consume. Library-first: you always see
it, pick a workout by number and act on it without retyping (show / run /
driven / delete). Grouped sections, English, minimal words for a clean,
readable terminal.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from src.application import library
from src.ui.cli.style import title, info, error, success, prompt, stage_label


# ---------------------------------------------------------------------------
# Robust input (EOF/Ctrl-C -> None = cancel/quit)
# ---------------------------------------------------------------------------

def _ask(text: str) -> Optional[str]:
    try:
        return input(prompt(text)).strip()
    except (EOFError, KeyboardInterrupt):
        return None


def _yes(text: str) -> bool:
    r = _ask(text)
    return r is not None and r.lower() in ("y", "yes")


def _pause() -> None:
    _ask("\n[ENTER to continue]")


def _k(key: str) -> str:
    """Key hint, e.g. (c) — highlighted so it pops in the terminal."""
    return success(f"({key})")


# ---------------------------------------------------------------------------
# Render: main hub
# ---------------------------------------------------------------------------

def _print_main(files: List[Path]) -> None:
    print(title("\n══════════════  RawTrainer  ══════════════"))
    if files:
        print(info(f"Library ({len(files)}) — pick a number:"))
        for i, f in enumerate(files, start=1):
            print(f"  {i:>2}) {library.peek_name(f)}")
    else:
        print(info("Library empty — (c) Create or (l) Load."))
    print()
    print(stage_label(" Workout"))
    print(f"   {_k('c')} Create · manual      {_k('l')} Load · file")
    print()
    print(stage_label(" Memory"))
    print(f"   {_k('t')} Tag search    {_k('s')} List stages    {_k('j')} List jobs")
    print()
    print(f"   {_k('h')} Stats / History       {_k('q')} Quit")
    print(title("══════════════════════════════════════════"))


# ---------------------------------------------------------------------------
# Submenu: actions on one library workout
# ---------------------------------------------------------------------------

def _workout_actions(path: Path) -> None:
    from src.ui.cli import main_cli  # lazy: avoid circular import
    while True:
        name = library.peek_name(path)
        print(title(f"\n── {name} ──"))
        print(stage_label(" Show"))
        print(f"   {_k('c')} Compact       {_k('f')} Full")
        print()
        print(stage_label(" Run"))
        print(f"   {_k('1')} Own pace      {_k('2')} Fully driven")
        print()
        print(stage_label(" Manage"))
        print(f"   {_k('d')} Delete")
        print()
        print(f"   {_k('b')} Back")
        choice = _ask("> ")
        if choice is None:
            return
        c = choice.lower()
        if c in ("b", "0", ""):
            return
        if c == "c":
            main_cli.cmd_preview(str(path), full=False)
        elif c == "f":
            main_cli.cmd_preview(str(path), full=True)
        elif c == "1":
            main_cli.cmd_run(str(path))
        elif c == "2":
            main_cli.cmd_drive(str(path))
        elif c == "d":
            if _yes(f"Delete '{name}'? [y/N]: "):
                main_cli.cmd_remove(str(path))
                return  # file is gone
            continue
        else:
            print(error("Invalid option."))
            continue
        _pause()


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def menu_loop() -> int:
    from src.ui.cli import main_cli
    while True:
        files = library.library_files()
        _print_main(files)
        choice = _ask("> ")

        if choice is None or choice.lower() in ("q", "quit"):
            print(info("Bye."))
            return 0

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(files):
                _workout_actions(files[idx - 1])
            else:
                print(error("Number out of range."))
                _pause()
            continue

        key = choice.lower()
        if key == "c":
            main_cli.cmd_new()
            _pause()
        elif key == "l":
            p = _ask("Path to YAML file (ENTER cancels): ")
            if p:
                main_cli.cmd_load(p)
                _pause()
        elif key == "t":
            t = _ask("Tags (space-separated, ENTER cancels): ")
            if t:
                main_cli.cmd_find(t.split())
            _pause()
        elif key == "s":
            main_cli.cmd_stages()
            _pause()
        elif key == "j":
            main_cli.cmd_jobs()
            _pause()
        elif key == "h":
            main_cli.cmd_stats()
            _pause()
        else:
            print(error("Invalid option."))
            _pause()
