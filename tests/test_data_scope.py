# tests/test_data_scope.py
"""Per-user data isolation behind Cloudflare Access (data_scope override).

Global behaviour (no override) is covered by test_library.py / test_run_log.py;
here we assert that when a per-user root IS active, the library, registry and run
logs land under it and one user cannot see another's data.
"""
from __future__ import annotations

import textwrap

from src.application import library
from src.infrastructure import data_scope, run_log


class _Workout:
    name = "Scoped WOD"
    description = "x"


VALID = """
    name: Scoped Lib
    stages:
      - name: S
        jobs:
          - name: J
            mode: custom_sets
            rounds: 1
            exercises:
              - name: Squat
                reps: 5
"""


def test_user_key_stable_and_filesystem_safe():
    assert data_scope.user_key("Jo@Example.com ") == data_scope.user_key("jo@example.com")
    key = data_scope.user_key("a.b+tag@x.co")
    assert key and all(c.isalnum() or c == "-" for c in key)
    # emails that slug to the same string must not collide (hash suffix disambiguates)
    assert data_scope.user_key("a.b@x.com") != data_scope.user_key("a-b@x.com")


def test_run_log_isolated_per_user(tmp_path, monkeypatch):
    monkeypatch.setattr(run_log, "_project_root", lambda: tmp_path)  # global logs -> tmp
    root_a = tmp_path / "data" / "users" / "a"
    root_b = tmp_path / "data" / "users" / "b"

    with data_scope.use_root(root_a):
        rec = run_log.build_run_record_base(_Workout(), None, mode="driven")
        rec["ended_at"] = run_log.now_iso()
        rec["duration_seconds"] = 10
        path = run_log.save_run_record(rec)
        assert path.parent == root_a / ".run_logs_v2"
        assert len(run_log.load_all_records()) == 1

    with data_scope.use_root(root_b):
        assert run_log.load_all_records() == []          # B sees nothing of A
    assert run_log.load_all_records() == []               # global sees nothing of A


def test_library_isolated_per_user(tmp_path, monkeypatch):
    # keep the shared component cache out of the real repo during the test
    from src.application import components
    monkeypatch.setattr(components, "_project_root", lambda: tmp_path, raising=False)

    src = tmp_path / "external.yaml"
    src.write_text(textwrap.dedent(VALID), encoding="utf-8")
    root_a = tmp_path / "data" / "users" / "a"
    root_b = tmp_path / "data" / "users" / "b"

    with data_scope.use_root(root_a):
        dest, replaced = library.import_workout(src)
        assert dest.parent == root_a / "workouts_files"
        assert replaced is False
        assert dest in library.library_files()
        assert library.is_in_library(dest)

    with data_scope.use_root(root_b):
        assert library.library_files() == []             # B doesn't see A's import
