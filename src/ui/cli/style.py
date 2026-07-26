# src/ui/cli/style.py
"""Terminal styling + a tiny theme layer (old-school phosphor by default).

Theme is chosen by env var (accent colour of titles/frames/prompts):
    RAWTRAINER_THEME=retro    green phosphor   (default)
    RAWTRAINER_THEME=amber    amber CRT
    RAWTRAINER_THEME=cyan     cyan
    RAWTRAINER_THEME=classic  magenta (the old look)

Only the ACCENT changes; semantic colours (success=green, error=red) stay put,
and the driven-mode segment chips keep their own colours.
"""
from __future__ import annotations

import logging
import os

from colorama import init, Fore, Style

log = logging.getLogger(__name__)

# Initialise colorama (Windows support + auto-reset).
init(autoreset=True)

_THEMES = {
    "retro": Fore.GREEN,
    "amber": Fore.YELLOW,
    "cyan": Fore.CYAN,
    "classic": Fore.MAGENTA,
    "mono": Fore.WHITE,
}
_DEFAULT_THEME = "retro"


def _accent() -> str:
    name = (os.environ.get("RAWTRAINER_THEME") or _DEFAULT_THEME).strip().lower()
    return _THEMES.get(name, _THEMES[_DEFAULT_THEME])


# --- accent-tinted (theme) ---------------------------------------------------

def accent(text: str) -> str:
    return f"{_accent()}{text}{Style.RESET_ALL}"


def accent_b(text: str) -> str:
    return f"{Style.BRIGHT}{_accent()}{text}{Style.RESET_ALL}"


def title(text: str) -> str:
    """Main title (workout / global header)."""
    return accent(text)


def stage_title(text: str) -> str:
    return accent(text)


def job_title(text: str) -> str:
    return accent(text)


def workout_label(label: str) -> str:
    return accent_b(label)


def stage_label(label: str) -> str:
    return accent_b(label)


def job_label(label: str) -> str:
    return accent_b(label)


def hotkey(k: str) -> str:
    """A shortcut key like (c), highlighted in the accent colour."""
    return f"{Style.BRIGHT}{_accent()}({k}){Style.RESET_ALL}"


def rule(width: int = 34) -> str:
    """A horizontal rule in the accent colour."""
    return accent("─" * width)


def banner() -> list:
    """Compact old-school title banner (list of lines, already tinted)."""
    w = 32
    mid = " ▞▚  R A W T R A I N E R  · v2"
    mid = mid + " " * (w - len(mid)) if len(mid) < w else mid[:w]
    return [
        accent("╔" + "═" * w + "╗"),
        accent("║") + accent_b(mid) + accent("║"),
        accent("╚" + "═" * w + "╝"),
    ]


# --- semantic (fixed) --------------------------------------------------------

def success(text: str) -> str:
    return f"{Style.BRIGHT}{Fore.GREEN}{text}{Style.RESET_ALL}"


def error(text: str) -> str:
    return f"{Style.BRIGHT}{Fore.RED}{text}{Style.RESET_ALL}"


def info(text: str) -> str:
    """Informational text / values."""
    return f"{Fore.WHITE}{text}{Style.RESET_ALL}"


def exercise(text: str) -> str:
    return f"{text}{Style.RESET_ALL}"


def prompt(text: str) -> str:
    """Input prompt — tinted with the theme accent."""
    return f"{Style.BRIGHT}{_accent()}{text}{Style.RESET_ALL}"
