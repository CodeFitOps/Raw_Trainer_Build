#!/usr/bin/env python3
from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml  # pip install pyyaml


# =========================
# Data models
# =========================

@dataclass
class Exercise:
    NAME: str
    reps: Optional[int] = None
    weight: Optional[int] = None
    work_time_in_seconds: Optional[int] = None


@dataclass
class Job:
    NAME: str
    MODE: str
    description: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    EXERCISES: List[Exercise] = field(default_factory=list)


@dataclass
class Stage:
    NAME: str
    Description: Optional[str] = None
    JOBS: List[Job] = field(default_factory=list)


@dataclass
class Workout:
    NAME: str
    Description: Optional[str] = None
    STAGES: List[Stage] = field(default_factory=list)


# =========================
# Mode schemas (proto)
# =========================

MODE_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "custom_sets": {
        "label": "Custom sets / Superseries",
        "fields": [
            {"key": "Rounds", "label": "Rounds", "type": "int", "required": True},
            {
                "key": "Rest_between_exercises_in_seconds",
                "label": "Rest between exercises (sec)",
                "type": "int",
                "required": False,
            },
            {
                "key": "Rest_between_rounds_in_seconds",
                "label": "Rest between rounds (sec)",
                "type": "int",
                "required": False,
            },
            {
                "key": "cadence",
                "label": "Cadence (e.g. 2-4-1)",
                "type": "str",
                "required": False,
            },
            {
                "key": "Eccentric (NEG)",
                "label": "Eccentric (NEG)?",
                "type": "bool",
                "required": False,
            },
            {
                "key": "isometric (HOLD)",
                "label": "Isometric (HOLD)?",
                "type": "bool",
                "required": False,
            },
        ],
    },
    "TABATA": {
        "label": "TABATA",
        "fields": [
            {"key": "rounds", "label": "Rounds", "type": "int", "required": True},
            {
                "key": "work_time_in_seconds",
                "label": "Work time per round (sec)",
                "type": "int",
                "required": True,
            },
            {
                "key": "rest_time_in_seconds",
                "label": "Rest time per round (sec)",
                "type": "int",
                "required": True,
            },
        ],
    },
    "EMOM": {
        "label": "EMOM",
        "fields": [
            {"key": "Rounds", "label": "Rounds (minutes)", "type": "int", "required": True},
            {
                "key": "work_time_in_seconds",
                "label": "Work time per minute (sec) (default 60)",
                "type": "int",
                "required": False,
            },
        ],
    },
    "amrap": {
        "label": "AMRAP",
        "fields": [
            {
                "key": "work_time_in_minutes",
                "label": "Total time (minutes)",
                "type": "int",
                "required": True,
            },
        ],
    },
    "for_time": {
        "label": "For time / chipper",
        "fields": [],
    },
}


EXERCISE_LIBRARY = [
    "Wall Balls",
    "Deadlifts",
    "Kettlebell Swings",
    "Box Jumps",
    "Push-ups",
    "Jumping Pull-ups",
    "Walking Lunge Steps",
    "Knees-to-elbows",
    "Push Presses",
    "Back Extensions",
    "Burpees",
    "Double-unders",
    "Run 400 m",
    "Jumping Jacks",
    "Bench Press",
]


# =========================
# Helpers
# =========================

def slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-") or "workout"


def ask(prompt: str, default: Optional[str] = None, required: bool = False) -> str:
    while True:
        if default is not None and default != "":
            raw = input(f"{prompt} [{default}]: ").strip()
        else:
            raw = input(f"{prompt}: ").strip()

        if not raw and default is not None:
            return default
        if required and not raw:
            print("Este campo es obligatorio.")
            continue
        return raw


def yes_no(prompt: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{prompt} ({d}): ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes", "s", "si", "sí"):
            return True
        if raw in ("n", "no"):
            return False
        print("Responde 'y' o 'n'.")


def choose_from_list(prompt: str, options: List[str]) -> str:
    print(prompt)
    for idx, opt in enumerate(options, start=1):
        print(f"  {idx}) {opt}")
    while True:
        raw = input("Opción: ").strip()
        if raw == "" and options:
            return options[0]
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        print("Opción inválida.")


def parse_bool_from_input(raw: str) -> Optional[bool]:
    if raw == "":
        return None
    raw = raw.strip().lower()
    if raw in ("y", "yes", "s", "si", "sí", "true", "1"):
        return True
    if raw in ("n", "no", "false", "0"):
        return False
    print("No entiendo eso como booleano, usando None.")
    return None


def ask_typed(field_conf: Dict[str, Any]) -> Any:
    key = field_conf["key"]
    label = field_conf.get("label", key)
    ftype = field_conf.get("type", "str")
    required = field_conf.get("required", False)

    while True:
        raw = ask(label, default="", required=required)
        if raw == "":
            return None
        try:
            if ftype == "int":
                return int(raw)
            elif ftype == "bool":
                val = parse_bool_from_input(raw)
                if val is None and required:
                    print("Campo obligatorio, responde sí o no.")
                    continue
                return val
            else:
                return raw
        except ValueError:
            print(f"Valor inválido para {label}. Esperaba {ftype}.")


# =========================
# Builders
# =========================

def ask_exercise() -> Exercise:
    print("\n--- Nuevo ejercicio ---")
    print("Elige de la lista o deja vacío para escribir a mano.")
    for idx, ex in enumerate(EXERCISE_LIBRARY, start=1):
        print(f"  {idx}) {ex}")
    raw = input("Número de ejercicio (o vacío para custom): ").strip()
    if raw.isdigit():
        idx = int(raw)
        if 1 <= idx <= len(EXERCISE_LIBRARY):
            name = EXERCISE_LIBRARY[idx - 1]
        else:
            name = ask("Nombre del ejercicio", required=True)
    else:
        name = ask("Nombre del ejercicio", required=True)

    reps_raw = ask("Reps (vacío si no aplica)", default="")
    weight_raw = ask("Peso (kg, vacío si no aplica)", default="")
    work_raw = ask("work_time_in_seconds (vacío si no aplica)", default="")

    reps = int(reps_raw) if reps_raw else None
    weight = int(weight_raw) if weight_raw else None
    work = int(work_raw) if work_raw else None

    return Exercise(NAME=name, reps=reps, weight=weight, work_time_in_seconds=work)


def ask_job(job_index: int) -> Job:
    print(f"\n===== JOB #{job_index} =====")
    name_default = f"Job {job_index}"
    name = ask("Nombre del JOB", default=name_default, required=True)

    mode_keys = list(MODE_SCHEMAS.keys())
    print("\nTipos de MODE disponibles:")
    for k, v in MODE_SCHEMAS.items():
        print(f"  - {k}: {v.get('label', '')}")
    mode = choose_from_list("Elige MODE", mode_keys)

    desc = ask("Descripción del JOB", default="")

    schema = MODE_SCHEMAS[mode]
    extra: Dict[str, Any] = {}
    for field_conf in schema.get("fields", []):
        val = ask_typed(field_conf)
        if val is not None:
            extra[field_conf["key"]] = val

    exercises: List[Exercise] = []
    while yes_no("¿Añadir ejercicio a este JOB?", default=(len(exercises) == 0)):
        exercises.append(ask_exercise())

    return Job(
        NAME=name,
        MODE=mode,
        description=desc or None,
        extra=extra,
        EXERCISES=exercises,
    )


def ask_stage(stage_index: int) -> Stage:
    print(f"\n===== STAGE #{stage_index} =====")
    name_default = f"Stage {stage_index}"
    name = ask("Nombre del STAGE", default=name_default, required=True)
    desc = ask("Descripción del STAGE", default="")

    jobs: List[Job] = []
    j = 1
    while True:
        jobs.append(ask_job(j))
        j += 1
        if not yes_no("¿Añadir otro JOB a este STAGE?", default=False):
            break

    return Stage(NAME=name, Description=desc or None, JOBS=jobs)


def build_workout() -> Workout:
    print("===== RAWTRAINER WORKOUT WIZARD (proto) =====\n")
    name = ask("Nombre del workout", required=True)
    desc = ask("Descripción del workout", default="")

    stages: List[Stage] = []
    i = 1
    while True:
        stages.append(ask_stage(i))
        i += 1
        if not yes_no("¿Añadir otro STAGE?", default=False):
            break

    return Workout(NAME=name, Description=desc or None, STAGES=stages)


# =========================
# YAML conversion / save
# =========================

def workout_to_yaml_dict(workout: Workout) -> Dict[str, Any]:
    d = asdict(workout)
    # Job.extra -> subir claves al mismo nivel que NAME/MODE/description
    for stage in d["STAGES"]:
        for job in stage["JOBS"]:
            extra = job.pop("extra", {}) or {}
            job.update(extra)
    return d


def save_workout_yaml(workout: Workout, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    base = slugify(workout.NAME)
    date_str = datetime.date.today().isoformat()
    filename = f"{date_str}-{base}.yaml"
    path = out_dir / filename

    data = workout_to_yaml_dict(workout)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

    return path


def main() -> None:
    out_dir = Path("workouts")  # ajusta esto a tu estructura real

    workout = build_workout()

    print("\n===== PREVIEW YAML =====")
    data = workout_to_yaml_dict(workout)
    print(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

    if yes_no("\n¿Guardar a fichero?", default=True):
        path = save_workout_yaml(workout, out_dir)
        print(f"\nGuardado en: {path}")
    else:
        print("\nNo se ha guardado el YAML, copia el preview si lo necesitas.")


if __name__ == "__main__":
    main()