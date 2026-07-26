# tests/test_i18n.py
"""i18n layer: language selection (env/override), formatting, fallbacks, and a
guard that the en/es catalogs stay in sync (same keys)."""
from __future__ import annotations

import pytest

from src import i18n


@pytest.fixture(autouse=True)
def _reset_language():
    i18n.set_language(None)
    yield
    i18n.set_language(None)


def test_default_is_english(monkeypatch):
    for v in ("RAWTRAINER_LANG", "RT_LANG", "LANG"):
        monkeypatch.delenv(v, raising=False)
    assert i18n.current_language() == "en"
    assert i18n.t("menu.quit") == "Quit"


def test_env_switches_to_spanish(monkeypatch):
    monkeypatch.setenv("RAWTRAINER_LANG", "ESP")
    assert i18n.current_language() == "es"
    assert i18n.t("menu.quit") == "Salir"


def test_override_beats_env(monkeypatch):
    monkeypatch.setenv("RAWTRAINER_LANG", "ESP")
    i18n.set_language("en")
    assert i18n.current_language() == "en"
    assert i18n.t("menu.quit") == "Quit"


def test_format_kwargs():
    i18n.set_language("en")
    assert i18n.t("menu.library_header", n=3) == "Library (3) — pick a number:"


def test_missing_key_falls_back_to_key():
    assert i18n.t("nope.nope") == "nope.nope"


def test_locale_style_lang_does_not_switch(monkeypatch):
    for v in ("RAWTRAINER_LANG", "RT_LANG"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    assert i18n.current_language() == "en"


def test_catalogs_have_same_keys():
    def flat(d, prefix=""):
        out = set()
        for k, v in (d or {}).items():
            key = f"{prefix}.{k}" if prefix else k
            out |= flat(v, key) if isinstance(v, dict) else {key}
        return out

    en = flat(i18n._catalog("en"))
    es = flat(i18n._catalog("es"))
    assert en == es, f"only in en={sorted(en - es)}  only in es={sorted(es - en)}"
