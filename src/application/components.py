# src/application/components.py
"""Biblioteca local de COMPONENTES reutilizables: stages y jobs por nombre.

Cada vez que se guarda un workout en la biblioteca, extraemos sus stages y sus
jobs y los guardamos aquí, indexados por nombre (slug). Así el builder puede
reutilizarlos: si escribes el nombre exacto de uno guardado, te lo ofrece.

Capa de aplicación (sin I/O de interfaz); la consumen CLI, menú y GUI futura.
Almacenamiento: un fichero YAML por componente en
  data/components/stages/<slug>.yaml
  data/components/jobs/<slug>.yaml
Mismo nombre = mismo componente (la última versión guardada gana).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.infrastructure.workout_registry import _project_root


def _components_root() -> Path:
    return _project_root() / "data" / "components"


def stages_dir() -> Path:
    return _components_root() / "stages"


def jobs_dir() -> Path:
    return _components_root() / "jobs"


def _slug(name: str) -> str:
    s = (name or "").strip().lower()
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in s) or "unnamed"


def _read_name(data: Any) -> Optional[str]:
    if isinstance(data, dict):
        n = data.get("name") or data.get("NAME")
        return str(n) if n else None
    return None


def _save_fragment(directory: Path, data: Dict[str, Any]) -> Optional[Path]:
    name = _read_name(data)
    if not name:
        return None
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / f"{_slug(name)}.yaml"
    with dest.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    return dest


def save_stage(stage: Dict[str, Any]) -> Optional[Path]:
    return _save_fragment(stages_dir(), stage)


def save_job(job: Dict[str, Any]) -> Optional[Path]:
    return _save_fragment(jobs_dir(), job)


def save_components_from_workout(workout: Dict[str, Any]) -> Dict[str, int]:
    """Extrae y guarda stages y jobs de un workout dict. Devuelve conteos."""
    counts = {"stages": 0, "jobs": 0}
    if not isinstance(workout, dict):
        return counts
    stages = workout.get("stages") or workout.get("STAGES") or []
    if not isinstance(stages, list):
        return counts
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        if save_stage(stage):
            counts["stages"] += 1
        jobs = stage.get("jobs") or stage.get("JOBS") or []
        if isinstance(jobs, list):
            for job in jobs:
                if isinstance(job, dict) and save_job(job):
                    counts["jobs"] += 1
    return counts


def rebuild_from_library() -> Dict[str, int]:
    """Reconstruye los componentes escaneando la biblioteca de workouts."""
    lib = _project_root() / "data" / "workouts_files"
    total = {"stages": 0, "jobs": 0}
    if not lib.is_dir():
        return total
    for p in sorted(lib.glob("*.yaml")):
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        r = save_components_from_workout(data)
        total["stages"] += r["stages"]
        total["jobs"] += r["jobs"]
    return total


def _list_names(directory: Path) -> List[str]:
    if not directory.is_dir():
        return []
    names: List[str] = []
    for p in sorted(directory.glob("*.yaml")):
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
            names.append(_read_name(data) or p.stem)
        except Exception:
            names.append(p.stem)
    return names


def stage_names() -> List[str]:
    return _list_names(stages_dir())


def job_names() -> List[str]:
    return _list_names(jobs_dir())


def _get(directory: Path, name: str) -> Optional[Dict[str, Any]]:
    if not name:
        return None
    p = directory / f"{_slug(name)}.yaml"
    if not p.is_file():
        return None
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def get_stage(name: str) -> Optional[Dict[str, Any]]:
    return _get(stages_dir(), name)


def get_job(name: str) -> Optional[Dict[str, Any]]:
    return _get(jobs_dir(), name)


def _tags_of(data: Any) -> List[str]:
    if isinstance(data, dict):
        t = data.get("tags")
        if isinstance(t, list):
            return [str(x).strip().lower() for x in t if str(x).strip()]
        if isinstance(t, str) and t.strip():
            return [t.strip().lower()]
    return []


def _by_tag(directory: Path, tags: List[str]) -> List[str]:
    """Nombres de componentes en `directory` que tengan ALGUNO de los tags (ANY)."""
    wanted = {t.strip().lower() for t in tags if t.strip()}
    out: List[str] = []
    if not wanted or not directory.is_dir():
        return out
    for p in sorted(directory.glob("*.yaml")):
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if wanted & set(_tags_of(data)):
            out.append(_read_name(data) or p.stem)
    return out


def stages_by_tag(tags: List[str]) -> List[str]:
    return _by_tag(stages_dir(), tags)


def jobs_by_tag(tags: List[str]) -> List[str]:
    return _by_tag(jobs_dir(), tags)
