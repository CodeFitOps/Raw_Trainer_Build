from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.application.workout_loader import load_workout_from_file, WorkoutLoadError
from src.domain.workout_model import Workout
from src.infrastructure.logging_setup import configure_logging
from src.ui.cli.preview import format_workout
from src.ui.cli.style import success, error, title, info
from src.infrastructure.workout_registry import WorkoutRegistry, _project_root

log = logging.getLogger(__name__)


# ======================================================================
# Auto-descubrimiento de YAMLs para importar
# ======================================================================

def _discover_yaml_candidates() -> list[Path]:
    """
    Busca ficheros .yml/.yaml en ubicaciones típicas del usuario:
    - ~/Downloads
    - ~/Documents
    - ~/
    - data/workouts_files (dentro del proyecto)
    """
    home = Path.home()
    candidate_dirs = [
        home,
        home / "Downloads",
        home / "Documents",
        _project_root() / "data" / "workouts_files",
    ]

    seen: set[Path] = set()
    files: list[Path] = []

    for d in candidate_dirs:
        if not d.is_dir():
            continue
        for pattern in ("*.yml", "*.yaml"):
            for p in d.glob(pattern):
                if p in seen:
                    continue
                seen.add(p)
                files.append(p)

    return sorted(files, key=lambda p: str(p).lower())


def _prompt_import_path() -> Path | None:
    """
    Lista candidatos auto-detectados y deja elegir número o path a mano.
    """
    candidates = _discover_yaml_candidates()

    if candidates:
        print("\nDetected YAML workouts in common folders:")
        for idx, p in enumerate(candidates, start=1):
            short = str(p).replace(str(Path.home()), "~")
            print(f"  {idx}) {short}")
        print("  0) Enter custom path")
    else:
        print("\nNo YAML workouts auto-detected.")
        print("Please enter a path manually.")

    while True:
        raw = input(
            "Choose file number or enter path (or 'c' to cancel): "
        ).strip()

        if raw.lower() in {"c", "q", "quit"}:
            return None

        if raw.isdigit() and candidates:
            idx = int(raw)
            if idx == 0:
                pass  # modo manual
            elif 1 <= idx <= len(candidates):
                return candidates[idx - 1]
            else:
                print(error("Invalid selection. Out of range."))
                continue

        path = Path(raw).expanduser()
        if path.is_file():
            return path

        print(error(f"Path '{raw}' does not exist or is not a file. Try again."))


# ======================================================================
# Utilidades comunes
# ======================================================================

def ask_yes_no(prompt: str, default: bool = False) -> bool:
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
        required=False,
    )

    # --- validate (DEV) ---
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate a workout YAML file (DEV, no registry update).",
    )
    validate_parser.add_argument(
        "workout_file",
        type=Path,
        help="Path to workout YAML file.",
    )

    # --- preview (DEV) ---
    preview_parser = subparsers.add_parser(
        "preview",
        help="Show a detailed summary of a workout YAML file (DEV, no registry).",
    )
    preview_parser.add_argument(
        "workout_file",
        type=Path,
        help="Path to workout YAML file.",
    )

    return parser.parse_args(argv)


# ======================================================================
# Handlers CLI
# ======================================================================

def _handle_validate(path: Path) -> int:
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
        success as success_style,
    )
    from src.ui.cli.preview import format_exercise_with_label

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

            # Rounds
            if job.rounds is not None:
                print(
                    "  "
                    + f"{job_label('Rounds:')} {info(str(job.rounds))}"
                )

            # Tiempos
            if job.work_time_in_seconds is not None:
                print(
                    "  "
                    + f"{job_label('Work time (job-level):')} "
                    f"{info(str(job.work_time_in_seconds) + 's')}"
                )
            if job.work_time_in_minutes is not None:
                print(
                    "  "
                    + f"{job_label('Work time (job-level):')} "
                    f"{info(str(job.work_time_in_minutes) + ' min')}"
                )

            # Descansos
            if job.rest_time_in_seconds is not None:
                print(
                    "  "
                    + f"{job_label('Rest time (between intervals):')} "
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

            # Cadence y flags técnicos
            if job.cadence:
                print(
                    "  "
                    + f"{job_label('Cadence:')} {info(job.cadence)}"
                )

            if getattr(job, "eccentric_neg", False):
                print(
                    "  "
                    + f"{job_label('Eccentric (NEG):')} "
                    f"{info('True')}"
                )

            if getattr(job, "isometric_hold", False):
                print(
                    "  "
                    + f"{job_label('Isometric (HOLD):')} "
                    f"{info('True')}"
                )

            # Ejercicios
            print("  " + f"{job_label('Exercises:')}")
            if not job.exercises:
                print("    " + info("(none)"))
            else:
                for ex in job.exercises:
                    print(
                        "    " + format_exercise_with_label(ex, job_label)
                    )

            input(prompt("\nPress Enter when you have finished this job..."))

    print(success_style("\n✅ Workout finished (manual mode)."))


def _handle_preview(path: Path) -> int:
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
    """
    Flujo de import:

    - Seleccionar path (auto-detect + manual).
    - Validar workout.
    - Pretty print.
    - Confirmar import.
    - Copiar a data/workouts_files.
    - Actualizar registry.
    - Opcionalmente ejecutar.
    """
    src_path = _prompt_import_path()
    if src_path is None:
        return 0

    log.info("CLI import called with file: %s", src_path)

    try:
        workout = load_workout_from_file(src_path)
    except WorkoutLoadError as exc:
        print(error("❌ Workout INVALID. Import aborted."))
        print(error(f"   Error: {exc}"))
        log.error("Import validation failed: %s", exc)
        return 1

    print(success("✅ Workout is VALID.\n"))
    print(format_workout(workout))

    if not ask_yes_no("Import this workout to local repository?", default=False):
        print(info("Import cancelled."))
        return 0

    project_root = _project_root()
    dest_dir = project_root / "data" / "workouts_files"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / src_path.name

    if dest_path.exists():
        if not ask_yes_no(
            f"File {dest_path.name} exists in data/workouts_files. Overwrite?",
            default=False,
        ):
            print(info("Import cancelled."))
            return 0

    import shutil

    try:
        shutil.copy2(src_path, dest_path)
    except Exception as exc:  # noqa: BLE001
        print(error(f"❌ Error copying file: {exc}"))
        log.error("Error copying workout file: %s → %s: %s", src_path, dest_path, exc)
        return 1

    registry = WorkoutRegistry.load()
    registry.register_import(
        file_path=dest_path,
        name=getattr(workout, "name", None),
        description=getattr(workout, "description", None),
        checksum=None,
    )
    registry.save()

    rel_dest = dest_path.relative_to(project_root)
    print(success(f"✅ Workout imported as: {rel_dest}"))
    print(info("This workout will now appear in 'Run Workout' menu."))

    if ask_yes_no("Run this workout now?", default=False):
        _run_workout_manual(workout)

    return 0


# ======================================================================
# main()
# ======================================================================

def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    configure_logging(
        debug=args.debug,
        log_file=args.log_file,
    )
    log.debug("CLI arguments: %r", args)

    if args.command == "validate":
        return _handle_validate(args.workout_file)

    if args.command == "preview":
        return _handle_preview(args.workout_file)

    # Sin subcomando: menú interactivo
    from src.ui.cli.menu import menu_loop

    log.info("No subcommand provided, entering interactive menu mode.")
    return menu_loop(
        run_fn=_handle_preview,
        import_fn=_handle_import_workout,
    )


if __name__ == "__main__":
    raise SystemExit(main())