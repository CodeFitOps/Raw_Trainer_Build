# src/ui/cli/menu.py
"""Enriched terminal menu: the RawTrainer hub.

Thin skin over the application layer (library, components) and the main_cli
handlers. Library-first: you always see it, pick a workout by number and act on
it without retyping. Compact, old-school phosphor look (theme via
RAWTRAINER_THEME), all text via i18n (`t`) so it switches with RAWTRAINER_LANG.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from src.application import library
from src.i18n import t
from src.ui.cli.style import (
    info, error, success, prompt, paint, hotkey, banner, rule,
)


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
    return r is not None and r.lower() in ("y", "yes", "s", "si", "sí")


def _pause() -> None:
    _ask(t("common.enter_continue"))


def _opt(key: str, label_key: str) -> str:
    """One compact option: (k) Label — key + label are separate theme roles."""
    return f"{hotkey(key)} {paint('option', t(label_key))}"


def _section(label_key: str, *opts: str) -> str:
    """A whole section on ONE line: ' HEADER  (a) X  (b) Y'."""
    head = paint("section", f" {t(label_key):<7}")
    return head + " " + "  ".join(opts)


# ---------------------------------------------------------------------------
# Render: main hub
# ---------------------------------------------------------------------------

def _print_main(files: List[Path]) -> None:
    for ln in banner():
        print(ln)
    if files:
        print(paint("lib_header", " " + t("menu.library_header", n=len(files))))
        for i, f in enumerate(files, start=1):
            print(f"  {paint('lib_num', str(i).rjust(2))} {paint('lib_name', library.peek_name(f))}")
    else:
        print(paint("lib_header", " " + t("menu.library_empty")))
    print(rule())
    print(_section("menu.sec_workout", _opt("c", "menu.create"), _opt("l", "menu.load")))
    print(_section("menu.sec_memory", _opt("t", "menu.tag_search"),
                   _opt("s", "menu.list_stages"), _opt("j", "menu.list_jobs")))
    print(_section("menu.sec_system", _opt("h", "menu.stats"), _opt("q", "menu.quit")))
    print(rule())


# ---------------------------------------------------------------------------
# Submenu: actions on one library workout
# ---------------------------------------------------------------------------

def _workout_actions(path: Path) -> None:
    from src.ui.cli import main_cli  # lazy: avoid circular import
    while True:
        name = library.peek_name(path)
        print(paint("submenu_title", f"\n── {name} ──"))
        print(_section("menu.sec_show", _opt("c", "menu.compact"), _opt("f", "menu.full")))
        print(_section("menu.sec_run", _opt("1", "menu.own_pace"), _opt("2", "menu.fully_driven")))
        print(_section("menu.sec_manage", _opt("d", "menu.delete"), _opt("b", "menu.back")))
        choice = _ask(t("menu.prompt"))
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
            if _yes(t("menu.confirm_delete", name=name)):
                main_cli.cmd_remove(str(path))
                return  # file is gone
            continue
        else:
            print(error(t("common.invalid")))
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
        choice = _ask(t("menu.prompt"))

        if choice is None or choice.lower() in ("q", "quit"):
            print(info(t("common.bye")))
            return 0

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(files):
                _workout_actions(files[idx - 1])
            else:
                print(error(t("menu.out_of_range")))
                _pause()
            continue

        key = choice.lower()
        if key == "c":
            main_cli.cmd_new()
            _pause()
        elif key == "l":
            p = _ask(t("menu.ask_path"))
            if p:
                main_cli.cmd_load(p)
                _pause()
        elif key == "t":
            tg = _ask(t("menu.ask_tags"))
            if tg:
                main_cli.cmd_find(tg.split())
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
            print(error(t("common.invalid")))
            _pause()
