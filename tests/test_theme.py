# tests/test_theme.py
"""Theme layer: selection, colour parsing, and guards that every theme has a
full 5-token palette and every UI role maps to a valid token/colour."""
from __future__ import annotations

import pytest

from src.ui.cli import style as S

# Roles the app paints (must all be mapped).
ROLES = {
    "banner", "rule", "lib_header", "lib_num", "lib_name", "section", "key",
    "option", "prompt", "submenu_title", "wk_name", "wk_desc", "stage_name",
    "stage_desc", "job_name", "job_desc", "meta_label", "meta_value",
    "ex_name", "ex_value", "tag", "success", "error", "info", "muted",
}


@pytest.fixture(autouse=True)
def _reset_theme():
    S.set_theme(None)
    yield
    S.set_theme(None)


def test_at_least_two_themes():
    assert len(S.available_themes()) >= 2


def test_env_selects_theme(monkeypatch):
    monkeypatch.setenv("RAWTRAINER_THEME", "amber")
    assert S.active_theme() == "amber"


def test_unknown_theme_falls_back(monkeypatch):
    monkeypatch.setenv("RAWTRAINER_THEME", "does-not-exist")
    assert S.active_theme() in S.available_themes()


def test_every_theme_has_full_palette():
    _, themes, _ = S._load()
    assert themes
    for name, spec in themes.items():
        pal = set((spec.get("palette") or {}).keys())
        missing = set(S.TOKENS) - pal
        assert not missing, f"theme {name} missing tokens: {sorted(missing)}"


def test_role_map_covers_all_roles():
    roles, _, _ = S._load()
    for r in ROLES:
        assert r in roles, f"role {r} not mapped"
        spec = roles[r]
        assert spec in S.TOKENS or S._fg(spec), f"role {r} -> invalid spec {spec!r}"


def test_resolve_uses_palette_token():
    S.set_theme("green")
    _, themes, _ = S._load()
    accent = themes["green"]["palette"]["accent"]
    # 'banner' maps to the accent token -> the theme's accent colour.
    assert S.code("banner") == S._fg(accent)


def test_paint_wraps_with_ansi_and_reset():
    S.set_theme("green")
    out = S.paint("banner", "X")
    assert out.startswith("\x1b[") and out.endswith("\x1b[0m") and "X" in out


def test_colour_parsing():
    assert S._fg("#ff8800") == "\x1b[38;2;255;136;0m"
    assert S._fg(82) == "\x1b[38;5;82m"
    assert S._fg("bright green") == "\x1b[92m"
    assert S._fg("green") == "\x1b[32m"
    assert S._fg("nonsense-colour") == ""
