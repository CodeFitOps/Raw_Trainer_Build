# tests/test_run_log.py
"""El record de sesión (driven o descriptivo) debe ser legible por stats_v2."""
from __future__ import annotations

from src.infrastructure import run_log
from src.infrastructure.stats_v2 import load_run_log


class _Workout:
    name = "Test WOD"
    description = "prueba"


def test_driven_record_roundtrip(tmp_path, monkeypatch):
    # Redirigir el directorio de logs al tmp del test.
    monkeypatch.setattr(run_log, "_project_root", lambda: tmp_path)

    rec = run_log.build_run_record_base(_Workout(), None, mode="driven")
    assert rec["session_mode"] == "driven"
    rec["ended_at"] = run_log.now_iso()
    rec["duration_seconds"] = 123
    path = run_log.save_run_record(rec)

    assert path.exists()
    assert path.parent == tmp_path / ".run_logs_v2"

    # stats_v2 debe leer el record y extraer nombre + duración.
    summary = load_run_log(path)
    assert summary is not None
    assert summary.workout_name == "Test WOD"
    assert summary.total_duration_seconds == 123
    assert summary.finished_at is not None


def test_stats_reads_fresh_canonical_even_with_legacy_dir(tmp_path, monkeypatch):
    """Regresión: aunque exista un dir legacy (run-logs-v2), stats debe incluir
    el log recién escrito en el canónico .run_logs_v2 (agrega todos los que existan)."""
    import src.infrastructure.stats_v2 as st

    monkeypatch.setattr(run_log, "_project_root", lambda: tmp_path)
    monkeypatch.setattr(st, "_project_root", lambda: tmp_path)
    (tmp_path / "run-logs-v2").mkdir()  # dir legacy vacío presente

    rec = run_log.build_run_record_base(_Workout(), None, mode="driven")
    rec["ended_at"] = run_log.now_iso()
    rec["duration_seconds"] = 42
    run_log.save_run_record(rec)  # escribe en el canónico .run_logs_v2

    report = st.build_stats_report()  # sin dir -> agrega los existentes
    assert "Test WOD" in report
