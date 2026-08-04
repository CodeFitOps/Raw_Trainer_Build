# src/ui/web/themes.py
"""Load the UI theme palette from config/themes.yaml and resolve it into complete token sets.

Single source of truth: the web UI's colours live in ``config/themes.yaml`` (repo root). Each
theme defines every token explicitly; a per-mode ``defaults`` block is still supported for
callers that want it, and a theme's ``colors`` overlay those. The loader *validates that every
declared token is defined for every theme* — so "all items in the UI are defined" is enforced
here rather than hoped for.

Web-only, no app deps beyond PyYAML (already a project dependency). Unit-testable in
isolation against any themes file.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# repo layout: <root>/src/ui/web/themes.py  ->  parents[3] == <root>
DEFAULT_THEMES_PATH = Path(__file__).resolve().parents[3] / "config" / "themes.yaml"


class ThemeError(ValueError):
    """Raised when the themes file is missing, malformed, or leaves a token undefined."""


class ThemePalette:
    """Parsed themes.yaml: the token catalogue, the per-mode defaults, and the theme list."""

    def __init__(self, tokens: Dict[str, str], defaults: Dict[str, Dict[str, str]],
                 themes: List[Dict[str, Any]]) -> None:
        self.tokens = tokens          # {token_name: human description}
        self.defaults = defaults      # {"light": {token: colour}, "dark": {...}}
        self._themes = themes         # raw list of {key, name, mode, colors}

    # ── loading ────────────────────────────────────────────────────────────────
    @classmethod
    def load(cls, path: Optional[Path] = None) -> "ThemePalette":
        p = Path(path) if path else DEFAULT_THEMES_PATH
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except FileNotFoundError as exc:
            raise ThemeError(f"themes file not found: {p}") from exc
        except yaml.YAMLError as exc:
            raise ThemeError(f"themes YAML is invalid: {exc}") from exc

        tokens = data.get("tokens")
        defaults = data.get("defaults") or {}
        themes = data.get("themes")
        if not isinstance(tokens, dict) or not tokens:
            raise ThemeError("themes.yaml: a non-empty `tokens` map is required")
        if not isinstance(themes, list) or not themes:
            raise ThemeError("themes.yaml: a non-empty `themes` list is required")
        if not isinstance(defaults, dict):
            raise ThemeError("themes.yaml: `defaults` must be a map of mode -> colours")

        # defaults may only reference declared tokens
        for mode, cols in defaults.items():
            if not isinstance(cols, dict):
                raise ThemeError(f"themes.yaml: defaults.{mode} must be a map")
            unknown = sorted(set(cols) - set(tokens))
            if unknown:
                raise ThemeError(f"themes.yaml: defaults.{mode} names unknown token(s) {unknown}")
        return cls(tokens, defaults, themes)

    # ── resolution ───────────────────────────────────────────────────────────────
    def _resolve_one(self, t: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(t, dict):
            raise ThemeError("each theme must be a map with key/name/mode/colors")
        key = t.get("key")
        mode = t.get("mode")
        if not key:
            raise ThemeError("a theme is missing its `key`")
        if not mode:
            raise ThemeError(f"theme {key!r} is missing its `mode`")

        colors = t.get("colors") or {}
        if not isinstance(colors, dict):
            raise ThemeError(f"theme {key!r}: `colors` must be a map")
        unknown = sorted(set(colors) - set(self.tokens))
        if unknown:
            raise ThemeError(f"theme {key!r}: unknown token(s) {unknown} — not declared in `tokens`")

        # start from the mode's shared defaults (if any), then apply this theme's overrides
        resolved: Dict[str, str] = dict(self.defaults.get(mode) or {})
        resolved.update(colors)

        missing = sorted(set(self.tokens) - set(resolved))
        if missing:
            raise ThemeError(
                f"theme {key!r} ({mode}): no colour for {missing} — every item must be defined "
                f"(add it under this theme's `colors:` or under defaults.{mode})"
            )
        for tok, val in resolved.items():
            if not isinstance(val, str) or not val.strip():
                raise ThemeError(f"theme {key!r}: token {tok!r} has a non-string/empty colour {val!r}")

        # emit only declared tokens, in the documented order — stable output for the client
        ordered = {tok: resolved[tok] for tok in self.tokens}
        return {"key": str(key), "name": str(t.get("name") or str(key).upper()),
                "mode": str(mode), "v": ordered}

    def resolved(self) -> List[Dict[str, Any]]:
        """All themes, each with a complete, validated token set (shape the client applies)."""
        seen = set()
        out = []
        for t in self._themes:
            r = self._resolve_one(t)
            if r["key"] in seen:
                raise ThemeError(f"duplicate theme key {r['key']!r}")
            seen.add(r["key"])
            out.append(r)
        return out

    def as_json(self) -> str:
        return json.dumps(self.resolved(), ensure_ascii=False, separators=(",", ":"))


def load_palette(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Convenience: resolved themes from the default (or given) themes.yaml."""
    return ThemePalette.load(path).resolved()
