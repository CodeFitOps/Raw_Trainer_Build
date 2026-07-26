# src/i18n.py
"""Tiny i18n layer for RawTrainer.

All user-facing text (labels, menus, instructions, prompts) goes through `t()`.
Strings live in one file per language under `src/ui/lang/<code>.yaml`.

Language is chosen by environment variable (default English):
    RAWTRAINER_LANG=ESP   (or RT_LANG, or LANG)  -> Spanish
    (unset / anything else)                       -> English

Values are case-insensitive and accept a few spellings (en/eng/english,
es/esp/spanish/español). Locale-style values like "en_US.UTF-8" do NOT switch
the app — only the explicit codes above — so the OS locale never surprises you.

A missing key falls back to the English catalog, then to the key itself, so the
app never crashes on a typo; you just see the raw key and know to add it.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

DEFAULT_LANG = "en"

# Explicit spellings only — never locale strings, so OS LANG can't switch us.
_ALIASES = {
    "en": "en", "eng": "en", "english": "en", "ingles": "en", "inglés": "en",
    "es": "es", "esp": "es", "spanish": "es",
    "espanol": "es", "español": "es", "castellano": "es",
}

# Env vars checked in order (namespaced first; bare LANG last).
_ENV_VARS = ("RAWTRAINER_LANG", "RT_LANG", "LANG")

_override: Optional[str] = None  # runtime override (tests / in-app switch)


def _lang_dir() -> Path:
    return Path(__file__).resolve().parent / "lang"


def _resolve(raw: Optional[str]) -> str:
    if not raw:
        return DEFAULT_LANG
    return _ALIASES.get(raw.strip().lower(), DEFAULT_LANG)


def current_language() -> str:
    """Active language code ('en'/'es'). Override > env vars > default."""
    if _override is not None:
        return _override
    for var in _ENV_VARS:
        val = os.environ.get(var)
        if val:
            code = _ALIASES.get(val.strip().lower())
            if code:
                return code
    return DEFAULT_LANG


def set_language(code: Optional[str]) -> None:
    """Force a language at runtime (None clears the override -> back to env)."""
    global _override
    _override = None if code is None else _resolve(code)
    # el catálogo se cachea por código, no por idioma activo; nada que invalidar


def available_languages() -> list:
    """Language codes that actually have a catalog file on disk."""
    d = _lang_dir()
    if not d.is_dir():
        return [DEFAULT_LANG]
    return sorted(p.stem for p in d.glob("*.yaml"))


@lru_cache(maxsize=None)
def _catalog(code: str) -> Dict[str, Any]:
    path = _lang_dir() / f"{code}.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _lookup(cat: Dict[str, Any], key: str) -> Optional[str]:
    cur: Any = cat
    for part in key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur if isinstance(cur, str) else None


def t(key: str, **kwargs: Any) -> str:
    """Translate `key` for the active language and .format() with kwargs.

    Falls back: active language -> English -> the key string itself.
    """
    lang = current_language()
    s = _lookup(_catalog(lang), key)
    if s is None and lang != DEFAULT_LANG:
        s = _lookup(_catalog(DEFAULT_LANG), key)
    if s is None:
        s = key
    if kwargs:
        try:
            return s.format(**kwargs)
        except Exception:
            return s
    return s
