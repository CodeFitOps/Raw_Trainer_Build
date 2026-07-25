# tests/test_library.py
"""Tests de la capa de aplicación (biblioteca): import (validar+guardar), resolve."""
from __future__ import annotations

import textwrap

import pytest

from src.application import library
from src.application.workout_loader import WorkoutLoadError

VALID = """
    name: Lib Test
    stages:
      - name: S
        jobs:
          - name: J
            mode: custom_sets
            rounds: 2
            exercises:
              - name: Squats
                reps: 10
"""

INVALID = """
    name: Bad
    stages:
      - name: S
        jobs:
          - name: J
            mode: nope
            rounds: 1
            exercises:
              - name: X
                reps: 1
"""


def test_import_valid_and_resolve(tmp_path, monkeypatch):
    lib = tmp_path / "lib"
    lib.mkdir()
    monkeypatch.setattr(library, "LIBRARY_DIR", lib)

    src = tmp_path / "external.yaml"
    src.write_text(textwrap.dedent(VALID), encoding="utf-8")

    dest, replaced = library.import_workout(src)
    assert dest.parent == lib
    assert dest.name == "external.yaml"
    assert replaced is False
    assert dest in library.library_files()
    # se resuelve por nombre y por número
    assert library.resolve("external") == dest
    assert library.resolve("1") == dest
    assert library.is_in_library(dest)


def test_import_invalid_not_stored(tmp_path, monkeypatch):
    lib = tmp_path / "lib"
    lib.mkdir()
    monkeypatch.setattr(library, "LIBRARY_DIR", lib)

    bad = tmp_path / "bad.yaml"
    bad.write_text(textwrap.dedent(INVALID), encoding="utf-8")

    with pytest.raises(WorkoutLoadError):
        library.import_workout(bad)
    # inválido => no se copia nada a la biblioteca
    assert list(lib.glob("*.yaml")) == []
