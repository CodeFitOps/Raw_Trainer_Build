# src/application/library.py
"""Capa de aplicación: gestión de la biblioteca de workouts.

Funciones puras (sin I/O de interfaz) que consumen por igual la CLI, el menú
de terminal y, en el futuro, la GUI. La 'biblioteca' es la carpeta
data/workouts_files; el registro JSON es metadato opcional (checksums, fechas).
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional, Tuple

import yaml

from src.application.workout_loader import (
    load_workout_v2_model_from_file,
    WorkoutLoadError,
)
from src.domain_v2.workout_v2 import WorkoutV2
from src.infrastructure.workout_registry import _project_root, WorkoutRegistry

SCHEMA_ROOT = _project_root() / "internal_tools" / "schemas"
LIBRARY_DIR = _project_root() / "data" / "workouts_files"


def library_files() -> list[Path]:
    """Ficheros YAML de la biblioteca, ordenados por nombre."""
    if not LIBRARY_DIR.is_dir():
        return []
    files = list(LIBRARY_DIR.glob("*.yaml")) + list(LIBRARY_DIR.glob("*.yml"))
    return sorted(files, key=lambda p: p.name.lower())


def peek_name(path: Path) -> str:
    """Lee solo el 'name' del YAML sin validar (para listados rápidos)."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            name = data.get("name") or data.get("NAME")
            if name:
                return str(name)
    except Exception:
        pass
    return path.stem


def resolve(arg: str) -> Optional[Path]:
    """Resuelve un argumento a un fichero de workout:
      1. Ruta existente.
      2. Número (índice de la biblioteca, ver library_files()).
      3. Nombre (stem exacto, o parcial si es único).
    Devuelve None si no lo encuentra.
    """
    p = Path(arg).expanduser()
    if p.is_file():
        return p
    files = library_files()
    if arg.isdigit():
        idx = int(arg)
        return files[idx - 1] if 1 <= idx <= len(files) else None
    low = arg.lower()
    for f in files:
        if f.stem.lower() == low or f.name.lower() == low:
            return f
    matches = [f for f in files if low in f.stem.lower()]
    return matches[0] if len(matches) == 1 else None


def load(path: Path) -> WorkoutV2:
    """Valida y construye el modelo de dominio (propaga WorkoutLoadError)."""
    return load_workout_v2_model_from_file(path=path, schema_root=SCHEMA_ROOT)


def is_in_library(path: Path) -> bool:
    try:
        return path.resolve().parent == LIBRARY_DIR.resolve()
    except Exception:
        return False


def import_workout(src_path: Path) -> Tuple[Path, bool]:
    """Valida un fichero externo y lo copia a la biblioteca (+registro opcional).

    Devuelve (ruta_destino, reemplazado). Lanza WorkoutLoadError si es inválido
    (en ese caso NO se copia nada).
    """
    workout = load(src_path)  # valida primero; si falla, propaga y no copiamos
    LIBRARY_DIR.mkdir(parents=True, exist_ok=True)
    dest = LIBRARY_DIR / src_path.name
    replaced = dest.exists()
    shutil.copy2(src_path, dest)
    try:
        registry = WorkoutRegistry.load()
        registry.register_import(
            file_path=dest, name=workout.name, description=workout.description
        )
        registry.save()
    except Exception:
        # el registro es metadato opcional; la fuente de verdad es la carpeta
        pass
    # Extraer stages y jobs a la biblioteca de componentes (para reutilizarlos).
    try:
        from src.application import components
        raw = yaml.safe_load(dest.read_text(encoding="utf-8"))
        components.save_components_from_workout(raw)
    except Exception:
        pass
    return dest, replaced


def remove_workout(arg: str) -> Optional[Path]:
    """Elimina de la biblioteca (por nombre/número/ruta). Devuelve la ruta
    borrada, o None si el argumento no resuelve a un fichero de la biblioteca."""
    path = resolve(arg)
    if path is None or not is_in_library(path):
        return None
    path.unlink()
    return path
