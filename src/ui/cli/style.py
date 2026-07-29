# src/ui/cli/style.py
"""Terminal styling with a small, consistent colour system.

Two levels, like real terminal apps:

  • PALETTE — each theme is just 5 tokens:
        accent  structure / headers / the theme's signature colour
        fg      primary readable text (names, values)
        dim     secondary text (descriptions, meta labels, rules, tags…)
        key     the interactive pop colour (hotkeys)
        alert   errors
  • ROLE MAP — every UI element (a ROLE: banner, lib_name, section, ex_value…)
        is mapped ONCE to a token, shared by all themes. So the whole app uses
        ~4-5 colours consistently, not 25.

Themes live in `src/themes.yaml` (5 hex per theme — drop in any colour family
to try it). A role may also point to a literal colour for a one-off exception.
Pick a theme with  RAWTRAINER_THEME=green  (amber | paper | slate | …).
Colours: "#rrggbb" truecolor, a 256 index, or a name ("bright green").
"""
from __future__ import annotations

import functools
import logging
import os
from pathlib import Path

import yaml
from colorama import init

log = logging.getLogger(__name__)
init(strip=False)  # never strip: we emit truecolor and want it passed through

_RESET = "\x1b[0m"
_override = None

TOKENS = ("accent", "fg", "dim", "key", "alert")

# Global role -> token map (mirrored in themes.yaml `roles:`; yaml wins if set).
_ROLES = {
    "banner": "accent",   "rule": "dim",          "lib_header": "accent",
    "lib_num": "dim",     "lib_name": "fg",        "section": "accent",
    "key": "key",         "option": "fg",          "prompt": "accent",
    "submenu_title": "accent",
    "wk_name": "accent",  "wk_desc": "dim",
    "stage_name": "accent", "stage_desc": "dim",
    "job_name": "accent", "job_desc": "dim",
    "meta_label": "dim",  "meta_value": "fg",
    "ex_name": "fg",      "ex_value": "accent",    "tag": "dim",
    "success": "accent",  "error": "alert",        "info": "fg",  "muted": "dim",
}

# Fallback theme if themes.yaml is missing (keeps the app usable).
_BUILTIN_THEMES = {
    "green": {"bg": "dark", "palette": {
        "accent": "#3fb96f", "fg": "#cfe3d6", "dim": "#5f836f",
        "key": "#d8a657", "alert": "#e05a4e"}},
}


def _themes_path() -> Path:
    return Path(__file__).resolve().parents[2] / "themes.yaml"


@functools.lru_cache(maxsize=1)
def _load():
    try:
        data = yaml.safe_load(_themes_path().read_text(encoding="utf-8")) or {}
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    roles = data.get("roles") if isinstance(data.get("roles"), dict) else None
    themes = data.get("themes") if isinstance(data.get("themes"), dict) else None
    default = data.get("default")
    themes = themes or _BUILTIN_THEMES
    default = default if default in themes else next(iter(themes))
    return (roles or _ROLES), themes, default


def available_themes() -> list:
    return sorted(_load()[1].keys())


def active_theme() -> str:
    if _override is not None:
        return _override
    _, themes, default = _load()
    env = (os.environ.get("RAWTRAINER_THEME") or "").strip().lower()
    return env if env in themes else default


def set_theme(name):
    """Force a theme at runtime (None -> back to env/default)."""
    global _override
    _override = name


def theme_bg(name: str = None) -> str:
    _, themes, _ = _load()
    return str((themes.get(name or active_theme()) or {}).get("bg", "dark"))


def palette(name: str = None) -> dict:
    """The 5 token colours of a theme."""
    _, themes, _ = _load()
    return dict((themes.get(name or active_theme()) or {}).get("palette") or {})


def role_token(role: str) -> str:
    """Which token a role maps to (for grouping / the swatch)."""
    roles, _, _ = _load()
    spec = roles.get(role, "fg")
    return spec if spec in TOKENS else "·"


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


def _resolve(theme: str, role: str):
    roles, themes, _ = _load()
    pal = (themes.get(theme) or {}).get("palette") or {}
    spec = roles.get(role, "fg")
    if spec in pal:                 # token -> its palette colour
        return pal[spec]
    if _fg(spec):                   # literal colour (per-role exception)
        return spec
    return pal.get("fg") or "white"  # unknown token -> primary text


@functools.lru_cache(maxsize=512)
def _code_cached(theme: str, role: str) -> str:
    return _fg(_resolve(theme, role))


def code(role: str) -> str:
    return _code_cached(active_theme(), role)


def paint(role: str, text: str) -> str:
    c = code(role)
    return f"{c}{text}{_RESET}" if c else str(text)


def paint_token(token: str, text: str) -> str:
    """Paint directly with a palette token (for the theme swatch)."""
    c = _fg(palette().get(token, "white"))
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
    """Compact old-school title banner (token: accent)."""
    w = 32
    mid = " ▞▚  R A W T R A I N E R  · v2"
    mid = mid + " " * (w - len(mid)) if len(mid) < w else mid[:w]
    return [
        paint("banner", "╔" + "═" * w + "╗"),
        paint("banner", "║" + mid + "║"),
        paint("banner", "╚" + "═" * w + "╝"),
    ]
