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


def format_exercise(ex, index, indent="    "):
    """Devuelve una línea legible para un ejercicio."""
    name = ex.get("NAME", "Unnamed exercise")
    reps = ex.get("reps")
    work_time = ex.get("work_time_in_seconds")

    if reps is not None and work_time is not None:
        return f"{indent}{index}) {name} – {reps} reps, {work_time} s"
    elif reps is not None:
        return f"{indent}{index}) {name} – {reps} reps"
    elif work_time is not None:
        return f"{indent}{index}) {name} – {work_time} s"
    else:
        return f"{indent}{index}) {name}"


def print_workout(data: dict):
    """Imprime el workout completo de forma legible (modo resumen)."""
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

            exercises = job.get("EXERCISES", [])
            if exercises:
                print("    Exercises:")
                for ei, ex in enumerate(exercises, start=1):
                    line = format_exercise(ex, ei)
                    print(line)
        print("\n" + "-" * 60)


def interactive_walkthrough(workout: dict):
    """
    Modo interactivo: muestra job a job.
    Espera a que el usuario pulse Enter para pasar al siguiente,
    o 'q' para salir.
    """
    name = workout.get("NAME", "Unnamed workout")
    desc = workout.get("Description") or workout.get("DESCRIPTION") or ""
    stages = workout.get("STAGES", [])

    print(f"\n=== MODO INTERACTIVO: {name} ===")
    if desc:
        print(desc)
    print("Irás viendo cada JOB uno a uno. Pulsa Enter para avanzar, 'q' para salir.\n")

    for si, stage in enumerate(stages, start=1):
        s_name = stage.get("NAME", f"Stage {si}")
        s_desc = stage.get("Description", "")

        print("=" * 60)
        print(f"Stage {si}: {s_name}")
        if s_desc:
            print(f"  {s_desc}")
        print("=" * 60)

        jobs = stage.get("JOBS", [])
        for ji, job in enumerate(jobs, start=1):
            j_name = job.get("NAME", f"Job {ji}")
            j_desc = job.get("description", "") or job.get("Description", "")
            rounds = job.get("Rounds")
            rest_ex = job.get("Rest_between_exercises_in_seconds")
            rest_rounds = job.get("Rest_between_rounds_in_seconds")
            cadence = job.get("cadence")
            exercises = job.get("EXERCISES", [])

            print("\n" + "-" * 60)
            print(f"Stage {si} - Job {ji}: {j_name}")
            print("-" * 60)

            if j_desc:
                print(f"Goal:\n  {j_desc}\n")

            if rounds is not None:
                print(f"Rounds: {rounds}")

            rest_lines = []
            r1 = format_rest("Rest between exercises", rest_ex)
            if r1:
                rest_lines.append(r1)
            r2 = format_rest("Rest between rounds", rest_rounds)
            if r2:
                rest_lines.append(r2)

            if rest_lines:
                print("Rest:")
                for rl in rest_lines:
                    print(rl)

            if cadence:
                print(f"Cadence: {cadence}")

            if exercises:
                print("\nExercises:")
                for ei, ex in enumerate(exercises, start=1):
                    line = format_exercise(ex, ei, indent="  ")
                    print(line)

            # Esperar interacción del usuario
            user_input = input(
                "\nPulsa Enter cuando termines este Job "
                "(o escribe 'q' y Enter para salir): "
            ).strip().lower()

            if user_input == "q":
                print("Saliendo del modo interactivo.")
                return

    print("\nHas completado todos los Jobs de este workout. GG.\n")


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

    # Soportar que el YAML tenga un workout (dict) o varios (lista)
    workouts = []
    if isinstance(data, list):
        workouts = data
    elif isinstance(data, dict):
        workouts = [data]
    else:
        print("Formato YAML inesperado.")
        sys.exit(1)

    # 1) Imprimir todos los workouts en modo resumen
    for w in workouts:
        print_workout(w)

    # 2) Preguntar si quieres modo interactivo
    answer = input(
        "\n¿Quieres entrar en modo interactivo job-a-job? [y/N]: "
    ).strip().lower()

    if answer == "y":
        # Por simplicidad: si hay varios workouts en la lista, recorremos todos
        for w in workouts:
            interactive_walkthrough(w)
    else:
        print("Modo interactivo cancelado. Fin.")


if __name__ == "__main__":
    main()
