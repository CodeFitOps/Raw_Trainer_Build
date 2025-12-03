#!/usr/bin/env python3
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Este script necesita PyYAML. Instálalo con: pip install pyyaml")
    sys.exit(1)


def format_rest(label: str, value):
    """Devuelve una línea de descanso si el valor existe y es > 0."""
    if value is None:
        return None
    try:
        v = int(value)
    except (TypeError, ValueError):
        return None
    if v <= 0:
        return None
    return f"    - {label}: {v} s"


def format_exercise(ex, index):
    """Devuelve una línea legible para un ejercicio."""
    name = ex.get("NAME", "Unnamed exercise")
    reps = ex.get("reps")
    work_time = ex.get("work_time_in_seconds")

    if reps is not None and work_time is not None:
        return f"    {index}) {name} – {reps} reps, {work_time} s"
    elif reps is not None:
        return f"    {index}) {name} – {reps} reps"
    elif work_time is not None:
        return f"    {index}) {name} – {work_time} s"
    else:
        return f"    {index}) {name}"


def print_workout(data: dict):
    name = data.get("NAME", "Unnamed workout")
    desc = data.get("Description") or data.get("DESCRIPTION") or ""

    print(f"WORKOUT: {name}")
    if desc:
        print(f"DESCRIPTION: {desc}")
    print("-" * 60)

    stages = data.get("STAGES", [])
    for si, stage in enumerate(stages, start=1):
        s_name = stage.get("NAME", f"Stage {si}")
        s_desc = stage.get("Description", "")
        print(f"\nStage {si}: {s_name}")
        if s_desc:
            print(f"  {s_desc}")

        jobs = stage.get("JOBS", [])
        for ji, job in enumerate(jobs, start=1):
            j_name = job.get("NAME", f"Job {ji}")
            j_desc = job.get("description", "") or job.get("Description", "")
            rounds = job.get("Rounds")
            rest_ex = job.get("Rest_between_exercises_in_seconds")
            rest_rounds = job.get("Rest_between_rounds_in_seconds")
            cadence = job.get("cadence")

            print(f"\n  Job {ji}: {j_name}")
            if j_desc:
                print(f"    Goal: {j_desc}")
            if rounds is not None:
                print(f"    Rounds: {rounds}")

            rest_lines = []
            r1 = format_rest("Rest between exercises", rest_ex)
            if r1:
                rest_lines.append(r1)
            r2 = format_rest("Rest between rounds", rest_rounds)
            if r2:
                rest_lines.append(r2)

            if rest_lines:
                print("    Rest:")
                for rl in rest_lines:
                    print(rl)

            if cadence:
                print(f"    Cadence: {cadence}")

            # Ejercicios
            exercises = job.get("EXERCISES", [])
            if exercises:
                print("    Exercises:")
                for ei, ex in enumerate(exercises, start=1):
                    line = format_exercise(ex, ei)
                    print(line)
        print("\n" + "-" * 60)


def main():
    if len(sys.argv) < 2:
        print("Uso: python print_workout.py workout.yaml")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"No se encontró el fichero: {path}")
        sys.exit(1)

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Soportar que el YAML tenga la workout directamente (dict)
    # o dentro de una lista (por si en el futuro hay varios workouts)
    if isinstance(data, list):
        for w in data:
            print_workout(w)
    elif isinstance(data, dict):
        print_workout(data)
    else:
        print("Formato YAML inesperado.")


if __name__ == "__main__":
    main()