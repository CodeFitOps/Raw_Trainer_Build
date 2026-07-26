# src/ui/cli/style.py
"""Terminal styling driven by a role-based colour theme.

Every UI element is a ROLE (banner, lib_name, section, key, wk_name, ex_value…);
a THEME maps each role to a colour. Themes live in `src/themes.yaml` (editable),
selected by env var:

    RAWTRAINER_THEME=retro     (amber | paper | slate | …)   default from the file

Colours may be truecolor "#rrggbb", a 256-index int, or a name ("bright green").
Call `paint(role, text)` (or the back-compat helpers below). Unknown role/theme
falls back to a readable default, so nothing ever crashes on a typo.
"""
from __future__ import annotations

import functools
import logging
import os
from pathlib import Path

import yaml
from colorama import init

log = logging.getLogger(__name__)

# Never strip: we emit truecolor SGR and want it to pass through untouched.
init(strip=False)

_RESET = "\x1b[0m"
_override = None  # runtime theme override (tests / in-app switch)


# ---------------------------------------------------------------------------
# Theme loading
# ---------------------------------------------------------------------------

def _themes_path() -> Path:
    return Path(__file__).resolve().parents[2] / "themes.yaml"


@functools.lru_cache(maxsize=1)
def _load():
    try:
        data = yaml.safe_load(_themes_path().read_text(encoding="utf-8")) or {}
    except Exception:
        data = {}
    themes = data.get("themes") if isinstance(data, dict) else None
    return (themes or {}), (data.get("default") if isinstance(data, dict) else None) or "retro"


def available_themes() -> list:
    themes, _ = _load()
    return sorted(themes.keys()) or ["retro"]


def active_theme() -> str:
    if _override is not None:
        return _override
    themes, default = _load()
    env = (os.environ.get("RAWTRAINER_THEME") or "").strip().lower()
    if env and env in themes:
        return env
    if default in themes:
        return default
    return next(iter(themes), "retro")


def set_theme(name):
    """Force a theme at runtime (None -> back to env/default)."""
    global _override
    _override = name


def theme_bg(name: str = None) -> str:
    themes, _ = _load()
    return str((themes.get(name or active_theme()) or {}).get("bg", "dark"))


# ---------------------------------------------------------------------------
# Colour spec -> ANSI foreground
# ---------------------------------------------------------------------------

_NAMES = {"black": 0, "red": 1, "green": 2, "yellow": 3,
          "blue": 4, "magenta": 5, "cyan": 6, "white": 7}


def _fg(spec) -> str:
    if spec is None:
        return ""
    if isinstance(spec, int):
        return f"\x1b[38;5;{spec}m"
    s = str(spec).strip()
    if not s:
        return ""
    if s.startswith("#") and len(s) == 7:
        try:
            r, g, b = int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16)
            return f"\x1b[38;2;{r};{g};{b}m"
        except ValueError:
            return ""
    if s.isdigit():
        return f"\x1b[38;5;{int(s)}m"
    low = s.lower()
    bright = low.startswith("bright ")
    if bright:
        low = low[7:]
    base = _NAMES.get(low)
    if base is None:
        return ""
    return f"\x1b[{90 + base}m" if bright else f"\x1b[{30 + base}m"


# Fallback if a role/theme is missing (keeps the app readable).
_FALLBACK = {"key": "bright yellow", "error": "bright red",
             "success": "bright green", "muted": "bright black"}


def _role_spec(theme: str, role: str):
    themes, _ = _load()
    roles = (themes.get(theme) or {}).get("roles") or {}
    if role in roles:
        return roles[role]
    return _FALLBACK.get(role, "white")


@functools.lru_cache(maxsize=512)
def _code_cached(theme: str, role: str) -> str:
    return _fg(_role_spec(theme, role))


def code(role: str) -> str:
    """Raw ANSI foreground prefix for a role (active theme)."""
    return _code_cached(active_theme(), role)


def paint(role: str, text: str) -> str:
    c = code(role)
    return f"{c}{text}{_RESET}" if c else str(text)


# ---------------------------------------------------------------------------
# Role helpers (used across the UI). Back-compat names kept.
# ---------------------------------------------------------------------------

def title(text: str) -> str:        return paint("wk_name", text)
def stage_title(text: str) -> str:  return paint("stage_name", text)
def job_title(text: str) -> str:    return paint("job_name", text)
def workout_label(t: str) -> str:   return paint("meta_label", t)
def stage_label(t: str) -> str:     return paint("stage_desc", t)
def job_label(t: str) -> str:       return paint("meta_label", t)
def info(text: str) -> str:         return paint("info", text)
def success(text: str) -> str:      return paint("success", text)
def error(text: str) -> str:        return paint("error", text)
def prompt(text: str) -> str:       return paint("prompt", text)
def muted(text: str) -> str:        return paint("muted", text)
def accent(text: str) -> str:       return paint("section", text)
def accent_b(text: str) -> str:     return paint("section", text)
def exercise(text: str) -> str:     return f"{text}{_RESET}"


def hotkey(k: str) -> str:
    return paint("key", f"({k})")


def rule(width: int = 34) -> str:
    return paint("rule", "─" * width)


def banner() -> list:
    """Compact old-school title banner (one colour: role `banner`)."""
    w = 32
    mid = " ▞▚  R A W T R A I N E R  · v2"
    mid = mid + " " * (w - len(mid)) if len(mid) < w else mid[:w]
    return [
        paint("banner", "╔" + "═" * w + "╗"),
        paint("banner", "║" + mid + "║"),
        paint("banner", "╚" + "═" * w + "╝"),
    ]
