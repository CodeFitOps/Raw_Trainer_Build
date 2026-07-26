# src/ui/cli/builder.py
"""Asistente interactivo (wizard) para montar un workout YAML paso a paso.

Piel fina sobre la capa de aplicación: usa `application.builder` para los
campos/validación de cada modo y `application.components` para reutilizar
stages y jobs guardados (autocompletar por nombre, ofreciendo y confirmando).
Devuelve un dict de workout listo para validar/guardar (o None si se cancela).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.application import builder as appbuilder
from src.application import components
from src.application import library
from src.ui.cli.style import prompt, title, info, error, success


# ---------------------------------------------------------------------------
# Prompts básicos (EOFError/KeyboardInterrupt -> cancelar limpio)
# ---------------------------------------------------------------------------

def _input(text: str) -> Optional[str]:
    try:
        return input(prompt(text)).strip()
    except (EOFError, KeyboardInterrupt):
        return None


def _yesno(question: str, default: bool = True) -> bool:
    d = "S/n" if default else "s/N"
    r = _input(f"{question} [{d}]: ")
    if r is None:
        return False
    if not r:
        return default
    return r.lower() in ("s", "si", "sí", "y", "yes")


def _required(label: str) -> Optional[str]:
    while True:
        v = _input(f"{label}: ")
        if v is None:
            return None
        if v:
            return v
        print(error("  (obligatorio)"))


def _optional(label: str) -> str:
    v = _input(f"{label}: ")
    return v or ""


def _field(label: str, typ: str, required: bool) -> Optional[Any]:
    hint = "obligatorio" if required else "ENTER salta"
    while True:
        raw = _input(f"{label} ({typ}, {hint}): ")
        if raw is None:
            return None
        if not raw:
            if required:
                print(error("      (obligatorio)"))
                continue
            return None
        try:
            return appbuilder.cast_value(raw, typ)
        except ValueError:
            print(error(f"      valor no válido para {typ}, reinténtalo"))


def _pick_mode() -> Optional[str]:
    modes = appbuilder.list_modes(library.SCHEMA_ROOT)
    print(info("    Modos disponibles: " + ", ".join(modes)))
    while True:
        v = _input("    Modo del job: ")
        if v is None:
            return None
        v = v.lower()
        if v in modes:
            return v
        print(error(f"    Modo no válido. Elige uno de: {', '.join(modes)}"))


# ---------------------------------------------------------------------------
# Construcción por niveles
# ---------------------------------------------------------------------------

def _build_exercise(mode: str) -> Optional[Dict[str, Any]]:
    name = _required("      Nombre del ejercicio")
    if name is None:
        return None
    ex: Dict[str, Any] = {"name": name}
    for f in appbuilder.exercise_scalar_fields(mode, library.SCHEMA_ROOT):
        val = _field(f"      {f['key']}", f["type"], f["required"])
        if val is not None:
            ex[f["key"]] = val
    return ex


def _build_job() -> Optional[Dict[str, Any]]:
    name = _required("    Nombre del job")
    if name is None:
        return None
    # Autocompletar: si el nombre coincide con uno guardado, ofrecer reutilizarlo.
    if name in components.job_names():
        if _yesno(f"    Ya tienes un job '{name}'. ¿Reutilizarlo entero?", default=True):
            saved = components.get_job(name)
            if saved:
                print(info(f"    ↳ reutilizado [{saved.get('mode', '?')}]"))
                return saved
    mode = _pick_mode()
    if mode is None:
        return None
    job: Dict[str, Any] = {"name": name, "mode": mode}
    for f in appbuilder.mode_scalar_fields(mode, library.SCHEMA_ROOT):
        val = _field(f"    {f['key']}", f["type"], f["required"])
        if val is not None:
            job[f["key"]] = val
    exercises: List[Dict[str, Any]] = []
    while _yesno(f"    ¿Añadir ejercicio #{len(exercises) + 1}?", default=True):
        ex = _build_exercise(mode)
        if ex is None:
            break
        exercises.append(ex)
    job["exercises"] = exercises
    print(info("    (nota: sets/tempo/intra_set/death_by y demás estructuras "
               "avanzadas se añaden editando el YAML)"))
    return job


def _build_stage() -> Optional[Dict[str, Any]]:
    name = _required("  Nombre del stage")
    if name is None:
        return None
    if name in components.stage_names():
        if _yesno(f"  Ya tienes un stage '{name}'. ¿Reutilizarlo entero (con sus jobs)?",
                  default=True):
            saved = components.get_stage(name)
            if saved:
                njobs = len(saved.get("jobs", []) or [])
                print(info(f"  ↳ reutilizado ({njobs} jobs)"))
                return saved
    stage: Dict[str, Any] = {"name": name}
    desc = _optional("  Descripción del stage (ENTER salta)")
    if desc:
        stage["description"] = desc
    jobs: List[Dict[str, Any]] = []
    while _yesno(f"  ¿Añadir job #{len(jobs) + 1} al stage '{name}'?", default=True):
        j = _build_job()
        if j is None:
            break
        jobs.append(j)
    stage["jobs"] = jobs
    return stage


def build_workout_interactive() -> Optional[Dict[str, Any]]:
    """Ejecuta el asistente y devuelve el workout dict (o None si se cancela)."""
    print(title("\n🛠  Builder de workout — móntalo paso a paso (Ctrl-C cancela)\n"))
    name = _required("Nombre del workout")
    if name is None:
        return None
    workout: Dict[str, Any] = {"name": name}
    desc = _optional("Descripción (ENTER salta)")
    if desc:
        workout["description"] = desc
    stages: List[Dict[str, Any]] = []
    while _yesno(f"¿Añadir stage #{len(stages) + 1}?", default=True):
        st = _build_stage()
        if st is None:
            break
        stages.append(st)
    workout["stages"] = stages
    return workout
