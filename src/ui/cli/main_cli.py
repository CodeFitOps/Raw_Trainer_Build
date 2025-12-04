# src/ui/cli/main_cli.py
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.application.workout_loader import load_workout_from_file, WorkoutLoadError
from src.domain.workout_model import Workout
from src.infrastructure.logging_setup import configure_logging
from src.ui.cli.preview import format_workout, format_exercise_with_label
from src.ui.cli.style import success, error, title, info

log = logging.getLogger(__name__)

def _handle_preview_interactive(path: Path) -> int:
    """
    Versión interactiva usada por el menú:
    - Carga y valida el workout.
    - Muestra el pretty print completo.
    - Pregunta si se vuelve al menú o se lanza el runner manual.
    """
    log.info("CLI preview (interactive) called with file: %s", path)
    try:
        workout = load_workout_from_file(path)
    except WorkoutLoadError as exc:
        print(error("❌ Cannot preview workout, it is INVALID."))
        print(error(f"   Error: {exc}"))
        log.error("Workout preview failed: %s", exc)
        return 1

    print(success("✅ Workout loaded successfully.\n"))
    print(format_workout(workout))

    from src.ui.cli.style import prompt  # evitar import circular en el top

    while True:
        print(info("\nOptions:"))
        print(info("  1) Return to menu"))
        print(info("  2) Run workout (manual, no timers)"))
        choice = input(prompt("> ")).strip()

        if choice == "1":
            return 0
        if choice == "2":
            _run_workout_manual(workout)
            return 0

        print(error("Invalid option. Please choose 1 or 2."))
def ask_yes_no(prompt: str, default: bool = False) -> bool:
    """
    Simple yes/no prompt for CLI usage.

    default=False  -> Enter vacío cuenta como "no"
    default=True   -> Enter vacío cuenta como "sí"
    """
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        answer = input(prompt + suffix).strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please answer 'y' or 'n'.")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="rawtrainer",
        description="RawTrainer CLI - workout validator and runner (WIP)",
    )

    # Global flags
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        help="Path to log file. If omitted, logs go only to stderr.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="subcommands",
        required=False,  # si no se especifica, decidimos en main()
    )

    # --- validate ---
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate a workout YAML file.",
    )
    validate_parser.add_argument(
        "workout_file",
        type=Path,
        help="Path to workout YAML file.",
    )

    # --- preview ---
    preview_parser = subparsers.add_parser(
        "preview",
        help="Load and show a detailed summary of a workout YAML file.",
    )
    preview_parser.add_argument(
        "workout_file",
        type=Path,
        help="Path to workout YAML file.",
    )

    return parser.parse_args(argv)


def _handle_validate(path: Path) -> int:
    """
    Subcommand: validate
    """
    log.info("CLI validate called with file: %s", path)
    try:
        _ = load_workout_from_file(path)
    except WorkoutLoadError as exc:
        print(error("❌ Workout is INVALID."))
        print(error(f"   Error: {exc}"))
        log.error("Workout validation failed: %s", exc)
        return 1

    print(success("✅ Workout is VALID according to domain model."))
    return 0

def _handle_preview(path: Path) -> int:
    """
    Subcommand: preview.

    - Carga y valida el workout.
    - Muestra el pretty print completo.
    - Pregunta si quieres ejecutar el workout en modo manual (sin timers).
    """
    log.info("CLI preview called with file: %s", path)
    try:
        workout = load_workout_from_file(path)
    except WorkoutLoadError as exc:
        print(error("❌ Cannot preview workout, it is INVALID."))
        print(error(f"   Error: {exc}"))
        log.error("Workout preview failed: %s", exc)
        return 1

    print(success("✅ Workout loaded successfully.\n"))
    print(format_workout(workout))

    print()
    if ask_yes_no("Run this workout now?", default=False):
        _run_workout_manual(workout)

    return 0

def _handle_import_workout() -> int:
    from src.application.workout_loader import load_workout_from_file, WorkoutLoadError
    # Pedir ruta al usuario
    path_str = input("Enter workout YAML path to import (or 'c' to cancel): ").strip()
    if path_str.lower() == 'c':
        return 0
    from pathlib import Path
    src_path = Path(path_str).expanduser()
    if not src_path.is_file():
        print(error(f"❌ File not found: {src_path}"))
        return 0

    log.info("CLI import called with file: %s", src_path)
    try:
        workout = load_workout_from_file(src_path)
    except WorkoutLoadError as exc:
        print(error("❌ Workout INVALID. Import aborted."))
        print(error(f"   Error: {exc}"))
        log.error("Import validation failed: %s", exc)
        return 1

    # Si pasa validación, presentamos resumen
    print(success("✅ Workout is VALID.\n"))
    print(format_workout(workout))

    # Preguntar confirmación
    if not ask_yes_no("Import this workout to local repository?", default=False):
        print(info("Import cancelled."))
        return 0

    # Copiar al directorio gestionado (data/workouts_files)
    project_root = Path(__file__).resolve().parents[2]
    dest_dir = project_root / "data" / "workouts_files"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / src_path.name
    if dest_path.exists():
        # Si ya existe, pedir confirmación para sobrescribir
        if ask_yes_no(f"File {dest_path.name} exists. Overwrite?", default=False):
            pass
        else:
            print(info("Import cancelled."))
            return 0

    try:
        import shutil
        shutil.copy2(src_path, dest_path)
    except Exception as exc:
        print(error(f"❌ Error copying file: {exc}"))
        log.error("Error copying workout file: %s → %s: %s", src_path, dest_path, exc)
        return 1

    print(success(f"✅ Workout imported: {dest_path.relative_to(project_root)}"))
    return 0

def _run_workout_manual(workout: Workout) -> None:
    """
    Runner manual sin timers: recorre stages y jobs.
    El usuario avanza pulsando Enter cuando termina cada job.
    """
    from src.ui.cli.style import (
        stage_title,
        stage_label,
        job_title,
        job_label,
        info,
        prompt,
        success,
    )

    print(title("\n=== Manual Workout Runner (no timers) ==="))
    print(title(f"Workout: {workout.name}\n"))

    for s_idx, stage in enumerate(workout.stages, start=1):
        print(stage_title(f"\n--- Stage {s_idx}: {stage.name} ---"))
        if stage.description:
            print(
                "  "
                + f"{stage_label('Description:')} {info(stage.description)}"
            )
        input(prompt("Press Enter to start this stage..."))

        for j_idx, job in enumerate(stage.jobs, start=1):
            print(
                job_title(f"\nJob {j_idx}: {job.name} [mode={job.mode.value}]")
            )
            if job.description:
                print(
                    "  "
                    + f"{job_label('Desc:')} {info(job.description)}"
                )

            if job.rounds is not None:
                print(
                    "  "
                    + f"{job_label('Rounds:')} {info(str(job.rounds))}"
                )

            if job.work_time_in_seconds is not None:
                print(
                    "  "
                    + f"{job_label('Work (job-level):')} "
                    f"{info(str(job.work_time_in_seconds) + 's')}"
                )
            if job.rest_time_in_seconds is not None:
                print(
                    "  "
                    + f"{job_label('Rest between intervals:')} "
                    f"{info(str(job.rest_time_in_seconds) + 's')}"
                )

            if job.rest_between_exercises_in_seconds is not None:
                print(
                    "  "
                    + f"{job_label('Rest between exercises:')} "
                    f"{info(str(job.rest_between_exercises_in_seconds) + 's')}"
                )
            if job.rest_between_rounds_in_seconds is not None:
                print(
                    "  "
                    + f"{job_label('Rest between rounds:')} "
                    f"{info(str(job.rest_between_rounds_in_seconds) + 's')}"
                )

            print("  " + f"{job_label('Exercises:')}")
            if not job.exercises:
                print("    " + info("(none)"))
            else:
                for ex in job.exercises:
                    print(
                        "    " + format_exercise_with_label(ex, job_label)
                    )

            input(prompt("\nPress Enter when you have finished this job..."))

    print(success("\n✅ Workout finished (manual mode)."))

def _handle_preview(path: Path) -> int:
    """
    Subcommand: preview.

    - Carga y valida el workout.
    - Muestra el pretty print completo.
    - Pregunta si quieres ejecutar el workout en modo manual (sin timers).
    """
    log.info("CLI preview called with file: %s", path)
    try:
        workout = load_workout_from_file(path)
    except WorkoutLoadError as exc:
        print(error("❌ Cannot preview workout, it is INVALID."))
        print(error(f"   Error: {exc}"))
        log.error("Workout preview failed: %s", exc)
        return 1

    print(success("✅ Workout loaded successfully.\n"))
    print(format_workout(workout))

    print()
    if ask_yes_no("Run this workout now?", default=False):
        _run_workout_manual(workout)

    return 0

def main(argv: list[str] | None = None) -> int:
    """
    Main entrypoint for the CLI.

    - Configura logging según flags globales.
    - Despacha a los subcomandos validate / preview.
    - Si no se especifica subcomando, entra en el menú interactivo.
    """
    args = _parse_args(argv)

    # Configuración de logging global
    configure_logging(
        debug=args.debug,
        log_file=args.log_file,
    )
    log.debug("CLI arguments: %r", args)

    if args.command == "validate":
        return _handle_validate(args.workout_file)

    if args.command == "preview":
        return _handle_preview(args.workout_file)

    # Sin subcomando: entramos en modo interactivo (menú).
    from src.ui.cli.menu import menu_loop

    log.info("No subcommand provided, entering interactive menu mode.")
    return menu_loop(
        validate_fn=_handle_validate,
        preview_and_run_fn=_handle_preview_interactive,
        import_fn=_handle_import_workout
    )


if __name__ == "__main__":
    raise SystemExit(main())
