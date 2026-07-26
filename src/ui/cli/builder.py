# src/ui/cli/builder.py
"""Asistente interactivo (wizard) para montar un workout YAML paso a paso.

Piel fina sobre la capa de aplicación: usa `application.builder` para los
campos/validación de cada modo y `application.components` para reutilizar
stages y jobs guardados — por nombre exacto (encuentra uno) o por tag (lista
y eliges). Pide tags en workout/stage/job. Devuelve un dict de workout listo
para validar/guardar (o None si se cancela).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.application import builder as appbuilder
from src.application import components
from src.application import library
from src.ui.cli.style import prompt, title, info, error, success


# ---------------------------------------------------------------------------
# Prompts básicos (EOFError/KeyboardInterrupt -> None = cancelar)
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


def _prompt_tags(label: str) -> List[str]:
    raw = _input(f"{label} (separados por espacio, ENTER salta): ")
    if not raw:
        return []
    return [t.strip() for t in raw.split() if t.strip()]


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
# Reutilización de componentes: por nombre exacto o por tag
# ---------------------------------------------------------------------------

def _reuse_by_name(kind: str) -> Optional[Dict[str, Any]]:
    names = components.stage_names() if kind == "stage" else components.job_names()
    if not names:
        print(info("  (no hay componentes guardados todavía)"))
        return None
    name = _input(f"  Nombre exacto del {kind} guardado: ")
    if not name:
        return None
    getter = components.get_stage if kind == "stage" else components.get_job
    data = getter(name)
    if data is None:
        print(error(f"  No encontrado: '{name}'"))
        return None
    return data


def _reuse_by_tag(kind: str) -> Optional[Dict[str, Any]]:
    raw = _input("  Tags a buscar (separados por espacio): ")
    if not raw:
        return None
    tags = [t for t in raw.split() if t]
    matcher = components.stages_by_tag if kind == "stage" else components.jobs_by_tag
    matches = matcher(tags)
    if not matches:
        print(info(f"  (ningún {kind} con esos tags)"))
        return None
    print(info(f"  {kind}s con {', '.join(tags)}:"))
    for i, n in enumerate(matches, start=1):
        print(f"    {i}) {n}")
    sel = _input("  Elige número (ENTER cancela): ")
    if not sel or not sel.isdigit():
        return None
    idx = int(sel)
    if not (1 <= idx <= len(matches)):
        return None
    getter = components.get_stage if kind == "stage" else components.get_job
    return getter(matches[idx - 1])


def _reuse_choice(kind: str):
    """(accion, data): 'cancel' | 'reuse'+dict | 'new'. Si la reutilización
    no encuentra nada, cae a 'new'."""
    print(info(f"  {kind}: [n]uevo · [r]eutilizar por nombre · [t]por tag  (ENTER = nuevo)"))
    c = _input("  Opción: ")
    if c is None:
        return ("cancel", None)
    c = c.strip().lower()
    if c == "r":
        data = _reuse_by_name(kind)
        return ("reuse", data) if data else ("new", None)
    if c == "t":
        data = _reuse_by_tag(kind)
        return ("reuse", data) if data else ("new", None)
    return ("new", None)


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
    action, data = _reuse_choice("job")
    if action == "cancel":
        return None
    if action == "reuse":
        print(info(f"    ↳ job reutilizado [{data.get('mode', '?')}]"))
        return data

    name = _required("    Nombre del job")
    if name is None:
        return None
    # Auto-ofrecer si el nombre coincide exacto con uno guardado.
    if name in components.job_names():
        if _yesno(f"    Ya existe un job '{name}'. ¿Reutilizarlo entero?", default=True):
            saved = components.get_job(name)
            if saved:
                print(info(f"    ↳ reutilizado [{saved.get('mode', '?')}]"))
                return saved

    mode = _pick_mode()
    if mode is None:
        return None
    job: Dict[str, Any] = {"name": name, "mode": mode}
    tags = _prompt_tags("    Tags del job")
    if tags:
        job["tags"] = tags
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
    print(info("    (nota: sets/tempo/intra_set/death_by se añaden editando el YAML)"))
    return job


def _build_stage() -> Optional[Dict[str, Any]]:
    action, data = _reuse_choice("stage")
    if action == "cancel":
        return None
    if action == "reuse":
        print(info(f"  ↳ stage reutilizado ({len(data.get('jobs', []) or [])} jobs)"))
        return data

    name = _required("  Nombre del stage")
    if name is None:
        return None
    if name in components.stage_names():
        if _yesno(f"  Ya existe un stage '{name}'. ¿Reutilizarlo entero (con sus jobs)?",
                  default=True):
            saved = components.get_stage(name)
            if saved:
                print(info(f"  ↳ reutilizado ({len(saved.get('jobs', []) or [])} jobs)"))
                return saved

    stage: Dict[str, Any] = {"name": name}
    tags = _prompt_tags("  Tags del stage")
    if tags:
        stage["tags"] = tags
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
    tags = _prompt_tags("Tags del workout")
    if tags:
        workout["tags"] = tags
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
