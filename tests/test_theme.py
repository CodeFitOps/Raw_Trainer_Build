# tests/test_theme.py
"""Theme layer: selection, colour parsing, and a guard that every theme
defines every role the UI actually paints."""
from __future__ import annotations

import pytest

from src.ui.cli import style as S

# Roles the app paints (must exist in every theme).
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


def test_all_themes_define_all_roles():
    themes, _ = S._load()
    assert themes, "no themes loaded"
    for name, spec in themes.items():
        roles = set((spec.get("roles") or {}).keys())
        missing = ROLES - roles
        assert not missing, f"theme {name} missing roles: {sorted(missing)}"


def test_paint_wraps_with_ansi_and_reset():
    S.set_theme("retro")
    out = S.paint("banner", "X")
    assert out.startswith("\x1b[") and out.endswith("\x1b[0m") and "X" in out


def test_colour_parsing():
    assert S._fg("#ff8800") == "\x1b[38;2;255;136;0m"
    assert S._fg(82) == "\x1b[38;5;82m"
    assert S._fg("bright green") == "\x1b[92m"
    assert S._fg("green") == "\x1b[32m"
    assert S._fg("nonsense-colour") == ""
