# tests/test_tag_search.py
"""Test de la búsqueda por tag: componentes (stages/jobs) y workouts."""
from __future__ import annotations

from src.application import components, library

TAGGED = {
    "name": "Tagged",
    "tags": ["legs"],
    "stages": [{"name": "Main", "tags": ["heavy"], "jobs": [
        {"name": "Squat", "mode": "custom_sets", "tags": ["squat", "legs"], "rounds": 3,
         "exercises": [{"name": "Back Squat", "reps": 5}]},
    ]}],
}


def test_components_by_tag(tmp_path, monkeypatch):
    monkeypatch.setattr(components, "_project_root", lambda: tmp_path)
    components.save_components_from_workout(TAGGED)
    assert components.stages_by_tag(["heavy"]) == ["Main"]
    assert components.jobs_by_tag(["legs"]) == ["Squat"]
    assert components.jobs_by_tag(["nope"]) == []
    # ANY match: basta con que coincida uno de los tags pedidos
    assert components.jobs_by_tag(["squat", "otro"]) == ["Squat"]
    # sin tags -> sin resultados
    assert components.stages_by_tag([]) == []


def test_workouts_by_tag(tmp_path, monkeypatch):
    monkeypatch.setattr(library, "LIBRARY_DIR", tmp_path)
    (tmp_path / "a.yaml").write_text("name: A\ntags: [legs]\nstages: []\n", encoding="utf-8")
    (tmp_path / "b.yaml").write_text("name: B\ntags: [arms]\nstages: []\n", encoding="utf-8")
    names = {n for _, n in library.workouts_by_tag(["legs"])}
    assert names == {"A"}
    assert library.workouts_by_tag(["nope"]) == []
