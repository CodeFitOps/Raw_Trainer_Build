"""Theme palette loader: resolves themes.yaml, enforces that every token is defined,
and must reproduce the palette the UI shipped with (no silent colour drift)."""
import copy
from pathlib import Path

import pytest

from src.ui.web.themes import ThemePalette, ThemeError, load_palette

# The palette the web UI shipped with (mirrors the former L_BASE/D_BASE/ACCENTS in index.html).
L_BASE = {
    "desk": "#d7d3d3", "bg": "#f3f2f2", "surface": "#eae9e9", "ink": "#201e1d", "ink2": "#2d2b2b",
    "n300": "#d7d3d3", "n400": "#bab6b6", "n500": "#9b9797", "n600": "#7d7979", "n700": "#605d5d", "n800": "#444141",
    "on-accent": "#ffffff", "field": "#ffffff",
    "stage-bg": "#201e1d", "stage-ink": "#f3f2f2", "stage-2": "#2d2b2b", "stage-line": "#444141",
    "stage-n300": "#d7d3d3", "stage-n400": "#bab6b6", "stage-n500": "#9b9797", "stage-n600": "#7d7979",
}
D_BASE = {
    "desk": "#0a0a09", "bg": "#141312", "surface": "#1e1c1b", "ink": "#ece9e6", "ink2": "#2a2827",
    "n300": "#302d2c", "n400": "#55514f", "n500": "#6e6a67", "n600": "#8b8683", "n700": "#a49f9c", "n800": "#bdb8b4",
    "on-accent": "#141312", "field": "#1e1c1b",
    "stage-bg": "#000000", "stage-ink": "#ece9e6", "stage-2": "#171615", "stage-line": "#2b2928",
    "stage-n300": "#cfcac7", "stage-n400": "#a39e9a", "stage-n500": "#8e8985", "stage-n600": "#807b77",
}
def _a(accent, a600, adeep, a100, a200, a300, abright, band):
    return {"accent": accent, "accent600": a600, "accent-deep": adeep, "accent100": a100,
            "accent200": a200, "accent300": a300, "accent-bright": abright, "band-accent": band}
ACCENTS = [
    ("red", "RED", "light", _a("#ec3013", "#dd2b0f", "#ae1800", "#fff2ef", "#ffe0d9", "#ffc4b8", "#ff9783", "#ff9783")),
    ("magenta", "MAGENTA", "light", _a("#b5127a", "#9c0c68", "#7d0a53", "#fdeff8", "#f9d9ee", "#f2b3dc", "#ef8fca", "#ef8fca")),
    ("blue", "BLUE", "light", _a("#1f4fd8", "#1740b8", "#14318f", "#eef2ff", "#dbe3ff", "#b9c8ff", "#8ea6ff", "#8ea6ff")),
    ("graphite", "GRAPHITE", "light", _a("#3c424b", "#2b3038", "#21252c", "#f0f1f3", "#dfe1e5", "#c3c7ce", "#a7adb6", "#a7adb6")),
    ("ember", "EMBER", "dark", _a("#ff7a5c", "#ff9179", "#ffa894", "#241715", "#331914", "#ffd0c4", "#ffb0a0", "#a83318")),
    ("orchid", "ORCHID", "dark", _a("#f18ad0", "#f6a3da", "#f9bce4", "#22141f", "#301827", "#f9d6ee", "#f9bce4", "#9c1f74")),
    ("sky", "SKY", "dark", _a("#7fb2ff", "#9cc4ff", "#bad6ff", "#121722", "#171f2e", "#d5e5ff", "#bad6ff", "#16418f")),
    ("ash", "ASH", "dark", _a("#c9c4c0", "#d8d4d1", "#e6e3e0", "#1a1918", "#232120", "#eceae8", "#e6e3e0", "#4a4644")),
]
def _expected():
    out = []
    for key, name, mode, acc in ACCENTS:
        v = dict(D_BASE if mode == "dark" else L_BASE)
        v.update(acc)
        # finer per-component items default to their source structural colour (mirrors themes.yaml)
        v.update({
            "btn-primary-bg": v["accent"], "btn-primary-ink": v["on-accent"],
            "header-bg": v["ink"], "header-ink": v["bg"],
            "row-num": v["accent-deep"], "row-line": v["n300"],
        })
        out.append({"key": key, "name": name, "mode": mode, "v": v})
    return out


def test_default_palette_matches_shipped_ui():
    got = load_palette()
    exp = _expected()
    assert [t["key"] for t in got] == [t["key"] for t in exp]
    for g, e in zip(got, exp):
        assert g["name"] == e["name"] and g["mode"] == e["mode"], g["key"]
        assert g["v"] == e["v"], f"{g['key']}: {set(g['v'].items()) ^ set(e['v'].items())}"


def test_every_theme_defines_every_token():
    pal = ThemePalette.load()
    toks = set(pal.tokens)
    for t in pal.resolved():
        assert set(t["v"]) == toks, t["key"]


def _palette(tokens=None, defaults=None, themes=None):
    return ThemePalette(
        tokens or {"bg": "d", "ink": "d", "accent": "d"},
        defaults if defaults is not None else {"light": {"bg": "#fff", "ink": "#000"}},
        themes if themes is not None else [{"key": "x", "name": "X", "mode": "light", "colors": {"accent": "#f00"}}],
    )


def test_missing_token_is_rejected():
    pal = _palette(themes=[{"key": "x", "mode": "light", "colors": {}}])  # no accent anywhere
    with pytest.raises(ThemeError) as e:
        pal.resolved()
    assert "accent" in str(e.value) and "every item must be defined" in str(e.value)


def test_unknown_token_is_rejected():
    pal = _palette(themes=[{"key": "x", "mode": "light", "colors": {"accent": "#f00", "nope": "#111"}}])
    with pytest.raises(ThemeError) as e:
        pal.resolved()
    assert "nope" in str(e.value)


def test_per_theme_can_override_any_token_not_just_accent():
    # a theme may recolour a base token (bg) for itself only
    pal = _palette(themes=[{"key": "x", "mode": "light", "colors": {"accent": "#f00", "bg": "#123456"}}])
    r = pal.resolved()[0]
    assert r["v"]["bg"] == "#123456" and r["v"]["ink"] == "#000"


def test_duplicate_key_is_rejected():
    pal = _palette(themes=[
        {"key": "x", "mode": "light", "colors": {"accent": "#f00"}},
        {"key": "x", "mode": "light", "colors": {"accent": "#0f0"}},
    ])
    with pytest.raises(ThemeError):
        pal.resolved()


def test_missing_file_raises_themeerror():
    with pytest.raises(ThemeError):
        ThemePalette.load(Path("/nonexistent/themes.yaml"))
