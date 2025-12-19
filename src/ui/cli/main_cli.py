from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.application.workout_loader import (
    load_workout_from_file,
    load_workout_v2_from_file,
    load_workout_v2_model_from_file,
    WorkoutLoadError,
)
from src.infrastructure.workout_registry import WorkoutRegistry, _project_root
from src.domain.workout_model import Workout
from src.infrastructure.logging_setup import configure_logging
from src.ui.cli.preview import format_workout
from src.ui.cli.preview_v2 import format_workout_v2
from src.ui.cli.style import success, error, title, info
from src.infrastructure.workout_registry import WorkoutRegistry, _project_root

from src.ui.cli.run_v2 import run_workout_v2_interactive
from src.infrastructure.stats_v2 import build_stats_report
from src.ui.cli.menu_v2 import menu_loop_v2


# Esto ya no lo necesitas realmente, pero si quieres lo puedes dejar:
SCHEMA_V2_ROOT = _project_root() / "internal_tools" / "schemas"
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
        description="RawTrainer CLI",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Optional log file path.",
    )

    subparsers = parser.add_subparsers(dest="command")

    # --- validate (v1) ---
    parser_validate = subparsers.add_parser(
        "validate",
        help="Validate a workout YAML using the v1 domain model.",
    )
    parser_validate.add_argument(
        "workout_file",
        type=Path,
        help="Path to workout YAML file.",
    )

    # --- preview (v1) ---
    parser_preview = subparsers.add_parser(
        "preview",
        help="Pretty-print a workout using the v1 domain model.",
    )
    parser_preview.add_argument(
        "workout_file",
        type=Path,
        help="Path to workout YAML file.",
    )

    # --- preview-v2 ---
    parser_preview_v2 = subparsers.add_parser(
        "preview-v2",
        help="Validate and pretty-print a workout using the v2 JSON-Schema + domain model.",
    )
    parser_preview_v2.add_argument(
        "workout_file",
        type=Path,
        help="Path to workout YAML file.",
    )
    parser_preview_v2.add_argument(
        "--schema-root",
        type=Path,
        default=SCHEMA_V2_ROOT,
        help="Root folder containing workout.schema.json and job.*.schema.json (default: internal_tools/schemas)",
    )

    # --- run-v2 (manual) ---
    parser_run_v2 = subparsers.add_parser(
        "run-v2",
        help="Run a workout (v2) in manual mode (no timers).",
    )
    parser_run_v2.add_argument(
        "workout_file",
        type=Path,
        help="Path to workout YAML file.",
    )
    parser_run_v2.add_argument(
        "--schema-root",
        type=Path,
        default=SCHEMA_V2_ROOT,
        help="Root folder containing workout.schema.json and job.*.schema.json (default: internal_tools/schemas)",
    )

    # --- stats-v2 ---
    subparsers.add_parser(
        "stats-v2",
        help="Show aggregated stats from v2 run logs.",
    )

    return parser.parse_args(argv)
# ======================================================================
# Handlers CLI
# ======================================================================

def _format_workout_v2_short(workout_v2) -> str:
    """
    Super short summary para evitar scroll:
    - Workout name + desc
    - Stages + Jobs
    - Exercises (solo nombre + reps/seconds si existen)
    """
    lines: list[str] = []
    lines.append(f"Workout: {workout_v2.name}")
    if getattr(workout_v2, "description", None):
        lines.append(f"Description: {workout_v2.description}")
    lines.append(f"Stages: {len(workout_v2.stages)}")
    lines.append("")

    for s_idx, stage in enumerate(workout_v2.stages, start=1):
        lines.append(f"Stage {s_idx}: {stage.name}")
        if getattr(stage, "description", None):
            lines.append(f"  - {stage.description}")
        lines.append(f"  Jobs: {len(stage.jobs)}")

        for j_idx, job in enumerate(stage.jobs, start=1):
            mode = getattr(job, "mode", None)
            mode_val = mode.value if mode is not None else "?"
            lines.append(f"    Job {j_idx}: {job.name} [{mode_val}]")

            # EXERCISES: solo lo mínimo
            exs = getattr(job, "exercises", []) or []
            if exs:
                lines.append("      Exercises:")
                for ex in exs:
                    ex_name = getattr(ex, "name", "?")
                    reps = getattr(ex, "reps", None)
                    wts = getattr(ex, "work_time_in_seconds", None)
                    if reps is not None:
                        lines.append(f"        - {ex_name}: {reps} reps")
                    elif wts is not None:
                        lines.append(f"        - {ex_name}: {wts}s")
                    else:
                        lines.append(f"        - {ex_name}")
        lines.append("")

    return "\n".join(lines).rstrip()

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

def _handle_preview_v2(path: Path) -> int:
    try:
        workout_v2 = load_workout_v2_model_from_file(
            path=path,
            schema_root=SCHEMA_V2_ROOT,
        )
    except WorkoutLoadError as exc:
        print(error(f"❌ Cannot preview v2 workout, it is INVALID.\n   Error: {exc}"))
        log.error("Workout v2 preview failed: %s", exc)
        return 1

    print(success("✅ Workout VALID according to JSON Schemas (v2)."))
    print()

    # ✅ resumen (NO full dump)
    from src.ui.cli.preview_v2 import format_workout_v2_summary, print_full_details_paginated
    print(format_workout_v2_summary(workout_v2))

    # ✅ opcional: full details paginado
    ans = input("Show full details (paginated)? [y/N]: ").strip().lower()
    if ans in {"y", "yes"}:
        print_full_details_paginated(workout_v2)

    return 0

def _handle_run_v2(path: Path) -> int:
    try:
        workout_v2 = load_workout_v2_model_from_file(
            path=path,
            schema_root=SCHEMA_V2_ROOT,
        )
    except WorkoutLoadError as exc:
        print(error(f"❌ Cannot run v2 workout, it is INVALID.\n   Error: {exc}"))
        log.error("Workout v2 run failed: %s", exc)
        return 1

    run_workout_v2_interactive(workout_v2)
    return 0

def _handle_import_workout() -> int:
    """
    Flujo de import:

    - Pide ruta al usuario.
    - Valida el workout:
        * primero con V2 + JSON Schema (si hay schemas)
        * luego con el modelo V1 (Workout) para mantener el runner actual
    - Pretty print completo.
    - Pregunta si quiere importar al repo local.
    - Copia a data/workouts_files.
    - Actualiza registry.
    - Opcionalmente, ejecuta el workout.
    """
    # 1) pedir ruta (o cancelar)
    path_str = input(
        "Choose file number or enter path (or 'c' to cancel): "
    ).strip()
    if path_str.lower() == "c":
        return 0

    src_path = Path(path_str).expanduser()
    if not src_path.is_file():
        print(error(f"❌ File not found: {src_path}"))
        return 0

    log.info("CLI import called with file: %s", src_path)

    # 2) Validación V2 (JSON Schema) si tenemos schema disponible
    if SCHEMA_V2_ROOT.is_dir():
        try:
            _ = load_workout_v2_from_file(
                path=src_path,
                schema_root=SCHEMA_V2_ROOT,
            )
        except WorkoutLoadError as exc:
            print(error("❌ Workout INVALID according to schema (V2). Import aborted."))
            print(error(f"   Error: {exc}"))
            log.error("Import schema-v2 validation failed: %s", exc)
            return 1
    else:
        log.debug(
            "Schema V2 root not found at %s, skipping JSON Schema validation.",
            SCHEMA_V2_ROOT,
        )

    # 3) Validación + parseo V1 (modelo actual) para pretty print + runner
    try:
        workout = load_workout_from_file(src_path)
    except WorkoutLoadError as exc:
        print(error("❌ Workout INVALID according to domain model (V1). Import aborted."))
        print(error(f"   Error: {exc}"))
        log.error("Import validation (V1) failed: %s", exc)
        return 1

    print(success("✅ Workout is VALID.\n"))
    print(format_workout(workout))

    # 4) Confirmar import real
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

    # 5) Actualizar registry
    registry = WorkoutRegistry.load()
    registry.register_import(
        file_path=dest_path,
        name=getattr(workout, "name", None),
        description=getattr(workout, "description", None),
    )
    registry.save()

    rel_dest = dest_path.relative_to(project_root)
    print(success(f"✅ Workout imported as: {rel_dest}"))
    print(info("This workout will now appear in 'Run Workout' menu."))

    # 6) Preguntar si corremos el workout ahora (runner V1 clásico)
    if ask_yes_no("Run this workout now?", default=False):
        _run_workout_manual(workout)

    return 0

def _menu_v2_entrypoint() -> int:
    return menu_loop_v2(
        preview_v2_fn=_handle_preview_v2,
        run_v2_fn=_handle_run_v2,
    )# ======================================================================
# main()
# ======================================================================

def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    # Config logging de forma segura aunque falten flags
    debug = getattr(args, "debug", False)
    log_file = getattr(args, "log_file", None)

    configure_logging(
        debug=getattr(args, "debug", False),
        log_file=getattr(args, "log_file", None),
    )
    log.debug("CLI arguments: %r", args)

    # ---------------- v1 commands ----------------
    if args.command == "validate":
        return _handle_validate(args.workout_file)

    if args.command == "preview":
        return _handle_preview(args.workout_file)

    # ---------------- v2 commands ----------------
    if args.command == "preview-v2":
        schema_root = getattr(args, "schema_root", SCHEMA_V2_ROOT)
        try:
            workout_v2 = load_workout_v2_model_from_file(
                path=args.workout_file,
                schema_root=schema_root,
            )
        except WorkoutLoadError as exc:
            print(
                error(
                    f"❌ Cannot preview v2 workout, it is INVALID.\n   Error: {exc}"
                )
            )
            log.error("Workout v2 preview failed: %s", exc)
            return 1

        print(success("✅ Workout VALID according to JSON Schemas (v2)."))
        print()
        print(format_workout_v2(workout_v2))
        return 0

    if args.command == "run-v2":
        schema_root = getattr(args, "schema_root", SCHEMA_V2_ROOT)
        try:
            workout_v2 = load_workout_v2_model_from_file(
                path=args.workout_file,
                schema_root=schema_root,
            )
        except WorkoutLoadError as exc:
            print(
                error(
                    f"❌ Cannot run v2 workout, it is INVALID.\n   Error: {exc}"
                )
            )
            log.error("Workout v2 run failed: %s", exc)
            return 1

        run_workout_v2_interactive(workout_v2)
        return 0

    if args.command == "stats-v2":
        from src.infrastructure.stats_v2 import RUN_LOGS_DIR

        report = build_stats_report(RUN_LOGS_DIR)
        print(report)
        return 0

    # ---------------- interactive menu (legacy) ----------------
    from src.ui.cli.menu import menu_loop

    log.info("No subcommand provided, entering interactive menu mode.")
    return menu_loop(
        run_fn=_handle_preview,
        import_fn=_handle_import_workout,
        v2_menu_fn=_menu_v2_entrypoint,
    )
if __name__ == "__main__":
    raise SystemExit(main())