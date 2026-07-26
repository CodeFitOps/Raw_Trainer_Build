# src/ui/cli/menu.py
"""Enriched terminal menu: the RawTrainer hub.

Thin skin over the application layer (library, components) and the main_cli
handlers — the same a future GUI would consume. Library-first: you always see
it, pick a workout by number and act on it without retyping (show / run /
driven / delete). All visible text goes through i18n (`t`), so the whole menu
switches language with RAWTRAINER_LANG.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from src.application import library
from src.i18n import t
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
    return r is not None and r.lower() in ("y", "yes", "s", "si", "sí")


def _pause() -> None:
    _ask(t("common.enter_continue"))


def _k(key: str) -> str:
    """Key hint, e.g. (c) — highlighted so it pops in the terminal."""
    return success(f"({key})")


# ---------------------------------------------------------------------------
# Render: main hub
# ---------------------------------------------------------------------------

def _print_main(files: List[Path]) -> None:
    print(title("\n══════════════  RawTrainer  ══════════════"))
    if files:
        print(info(t("menu.library_header", n=len(files))))
        for i, f in enumerate(files, start=1):
            print(f"  {i:>2}) {library.peek_name(f)}")
    else:
        print(info(t("menu.library_empty")))
    print()
    print(stage_label(t("menu.sec_workout")))
    print(f"   {_k('c')} {t('menu.create')}      {_k('l')} {t('menu.load')}")
    print()
    print(stage_label(t("menu.sec_memory")))
    print(f"   {_k('t')} {t('menu.tag_search')}    {_k('s')} {t('menu.list_stages')}    {_k('j')} {t('menu.list_jobs')}")
    print()
    print(f"   {_k('h')} {t('menu.stats')}       {_k('q')} {t('menu.quit')}")
    print(title("══════════════════════════════════════════"))


# ---------------------------------------------------------------------------
# Submenu: actions on one library workout
# ---------------------------------------------------------------------------

def _workout_actions(path: Path) -> None:
    from src.ui.cli import main_cli  # lazy: avoid circular import
    while True:
        name = library.peek_name(path)
        print(title(f"\n── {name} ──"))
        print(stage_label(t("menu.sec_show")))
        print(f"   {_k('c')} {t('menu.compact')}       {_k('f')} {t('menu.full')}")
        print()
        print(stage_label(t("menu.sec_run")))
        print(f"   {_k('1')} {t('menu.own_pace')}      {_k('2')} {t('menu.fully_driven')}")
        print()
        print(stage_label(t("menu.sec_manage")))
        print(f"   {_k('d')} {t('menu.delete')}")
        print()
        print(f"   {_k('b')} {t('menu.back')}")
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
