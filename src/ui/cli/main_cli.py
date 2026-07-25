# src/ui/cli/main_cli.py
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional, Tuple

from src.application import library
from src.application.workout_loader import WorkoutLoadError
from src.infrastructure.logging_setup import configure_logging
from src.ui.cli.preview_v2 import format_workout_v2_summary, format_workout_v2_full
from src.ui.cli.run_v2 import run_workout_v2_interactive
from src.infrastructure.stats_v2 import build_stats_report, RUN_LOGS_DIR
from src.ui.cli.style import success, error, title, info

log = logging.getLogger(__name__)


# ======================================================================
# Helpers
# ======================================================================

def _resolve_and_load(arg: str) -> Tuple[Optional[object], Optional[Path]]:
    path = library.resolve(arg)
    if path is None:
        print(error(f"❌ No encuentro el workout '{arg}'."))
        print(info("   Prueba 'list' para ver los disponibles."))
        return None, None
    try:
        workout = library.load(path)
    except WorkoutLoadError as exc:
        print(error(f"❌ Workout INVÁLIDO: {path.name}"))
        print(error(f"   {exc}"))
        return None, path
    return workout, path


def _ask(question: str) -> bool:
    return input(f"{question} [y/N]: ").strip().lower() in ("y", "yes", "s", "si", "sí")


# ======================================================================
# Handlers (adaptadores finos sobre la capa de aplicación)
# ======================================================================

def cmd_list() -> int:
    files = library.library_files()
    if not files:
        print(info(f"No hay workouts en {library.LIBRARY_DIR}"))
        return 0
    print(title(f"Workouts disponibles ({len(files)}):"))
    for idx, f in enumerate(files, start=1):
        print(f"  {idx:>2}) {f.name:<46} {info(library.peek_name(f))}")
    return 0


def cmd_validate(arg: str) -> int:
    workout, _ = _resolve_and_load(arg)
    if workout is None:
        return 1
    n_jobs = sum(len(s.jobs) for s in workout.stages)
    print(success(f"✅ VÁLIDO: {workout.name}  ({len(workout.stages)} stages, {n_jobs} jobs)"))
    return 0


def cmd_preview(arg: str, full: bool = False) -> int:
    workout, _ = _resolve_and_load(arg)
    if workout is None:
        return 1
    print(success("✅ Workout válido (v2).\n"))
    print(format_workout_v2_full(workout) if full else format_workout_v2_summary(workout))
    return 0


def cmd_run(arg: str) -> int:
    workout, path = _resolve_and_load(arg)
    if workout is None:
        return 1
    print(success(f"✅ {workout.name} — listo para ejecutar.\n"))
    print(format_workout_v2_summary(workout))
    print()
    run_workout_v2_interactive(workout, source_path=path)
    # Si es un fichero suelto (fuera de la biblioteca), ofrecer guardarlo.
    if path is not None and not library.is_in_library(path):
        if _ask("\n¿Guardar este workout en tu biblioteca?"):
            dest, replaced = library.import_workout(path)
            print(success(f"✅ Guardado como {dest.name}" + (" (reemplazado)" if replaced else "")))
    return 0


def cmd_load(arg: str) -> int:
    path = library.resolve(arg)
    if path is None:
        print(error(f"❌ No encuentro el fichero '{arg}'."))
        return 1
    try:
        dest, replaced = library.import_workout(path)
    except WorkoutLoadError as exc:
        print(error("❌ Workout INVÁLIDO — no se guarda."))
        print(error(f"   {exc}"))
        return 1
    print(success(f"✅ Cargado en tu biblioteca: {dest.name}" + (" (reemplazado)" if replaced else "")))
    print(info(f"   Ejecútalo con:  run {dest.stem}"))
    return 0


def cmd_remove(arg: str) -> int:
    path = library.remove_workout(arg)
    if path is None:
        print(error(f"❌ No está en tu biblioteca: '{arg}'."))
        return 1
    print(success(f"🗑  Eliminado de la biblioteca: {path.name}"))
    return 0


def cmd_stats() -> int:
    print(build_stats_report(RUN_LOGS_DIR))
    return 0


# ======================================================================
# CLI
# ======================================================================

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rawtrainer",
        description="RawTrainer — reproductor de entrenamientos por CLI.",
    )
    parser.add_argument("--debug", action="store_true", help="Logging de depuración.")
    parser.add_argument("--log-file", type=Path, default=None, help="Fichero de log opcional.")

    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", aliases=["run-v2"], help="Valida, muestra y ejecuta un workout.")
    p_run.add_argument("workout", help="Ruta, nombre o número (ver 'list').")

    p_prev = sub.add_parser("preview", aliases=["preview-v2"], help="Valida y muestra un workout (sin ejecutarlo).")
    p_prev.add_argument("workout", help="Ruta, nombre o número.")
    p_prev.add_argument("--full", action="store_true", help="Detalle completo (ejercicios, tiempos, descansos).")

    p_val = sub.add_parser("validate", help="Solo valida un workout (exit 0/1).")
    p_val.add_argument("workout", help="Ruta, nombre o número.")

    p_load = sub.add_parser("load", aliases=["import"], help="Valida un fichero y lo guarda en tu biblioteca.")
    p_load.add_argument("workout", help="Ruta a un fichero YAML.")

    p_rm = sub.add_parser("remove", aliases=["rm"], help="Elimina un workout de tu biblioteca.")
    p_rm.add_argument("workout", help="Nombre o número.")

    sub.add_parser("list", help="Lista los workouts de tu biblioteca.")
    sub.add_parser("stats", aliases=["stats-v2"], help="Estadísticas de tus sesiones.")
    sub.add_parser("menu", help="Menú interactivo de terminal (por defecto sin subcomando).")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    configure_logging(
        debug=getattr(args, "debug", False),
        log_file=getattr(args, "log_file", None),
    )
    log.debug("CLI args: %r", args)

    cmd = args.command
    try:
        if cmd in ("run", "run-v2"):
            return cmd_run(args.workout)
        if cmd in ("preview", "preview-v2"):
            return cmd_preview(args.workout, full=getattr(args, "full", False))
        if cmd == "validate":
            return cmd_validate(args.workout)
        if cmd in ("load", "import"):
            return cmd_load(args.workout)
        if cmd in ("remove", "rm"):
            return cmd_remove(args.workout)
        if cmd == "list":
            return cmd_list()
        if cmd in ("stats", "stats-v2"):
            return cmd_stats()
        if cmd == "menu":
            from src.ui.cli.menu import menu_loop
            return menu_loop()
        # sin subcomando -> menú interactivo de terminal
        from src.ui.cli.menu import menu_loop
        return menu_loop()
    except (KeyboardInterrupt, EOFError):
        print(info("\nCancelado."))
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
