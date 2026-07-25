# src/ui/cli/main_cli.py
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional, Tuple

from src.application.workout_loader import (
    load_workout_v2_model_from_file,
    WorkoutLoadError,
)
from src.infrastructure.workout_registry import _project_root
from src.infrastructure.logging_setup import configure_logging
from src.ui.cli.preview_v2 import (
    format_workout_v2_summary,
    format_workout_v2_full,
)
from src.ui.cli.run_v2 import run_workout_v2_interactive
from src.infrastructure.stats_v2 import build_stats_report, RUN_LOGS_DIR
from src.ui.cli.style import success, error, title, info

log = logging.getLogger(__name__)

SCHEMA_V2_ROOT = _project_root() / "internal_tools" / "schemas"
WORKOUTS_DIR = _project_root() / "data" / "workouts_files"


# ======================================================================
# Resolución de workouts (por ruta, número o nombre)
# ======================================================================

def _list_workout_files() -> list[Path]:
    if not WORKOUTS_DIR.is_dir():
        return []
    files = list(WORKOUTS_DIR.glob("*.yaml")) + list(WORKOUTS_DIR.glob("*.yml"))
    return sorted(files, key=lambda p: p.name.lower())


def resolve_workout(arg: str) -> Optional[Path]:
    """
    Resuelve el argumento a un fichero de workout:
      1. Ruta existente (tal cual).
      2. Número (índice de `list`).
      3. Nombre de fichero (con o sin extensión): exacto o parcial único.
    Devuelve None si no lo encuentra.
    """
    p = Path(arg).expanduser()
    if p.is_file():
        return p

    files = _list_workout_files()

    if arg.isdigit():
        idx = int(arg)
        return files[idx - 1] if 1 <= idx <= len(files) else None

    low = arg.lower()
    for f in files:
        if f.stem.lower() == low or f.name.lower() == low:
            return f
    matches = [f for f in files if low in f.stem.lower()]
    return matches[0] if len(matches) == 1 else None


def _load(arg: str) -> Tuple[Optional[object], Optional[Path]]:
    """Resuelve + valida + carga. Devuelve (WorkoutV2|None, Path|None)."""
    path = resolve_workout(arg)
    if path is None:
        print(error(f"❌ No encuentro el workout '{arg}'."))
        print(info("   Prueba 'list' para ver los disponibles."))
        return None, None
    try:
        workout = load_workout_v2_model_from_file(path=path, schema_root=SCHEMA_V2_ROOT)
    except WorkoutLoadError as exc:
        print(error(f"❌ Workout INVÁLIDO: {path.name}"))
        print(error(f"   {exc}"))
        return None, path
    return workout, path


# ======================================================================
# Handlers
# ======================================================================

def cmd_list() -> int:
    import yaml

    files = _list_workout_files()
    if not files:
        print(info(f"No hay workouts en {WORKOUTS_DIR}"))
        return 0
    print(title(f"Workouts disponibles ({len(files)}):"))
    for idx, f in enumerate(files, start=1):
        name = ""
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                name = str(data.get("name") or data.get("NAME") or "")
        except Exception:
            name = "(YAML inválido)"
        print(f"  {idx:>2}) {f.name:<46} {info(name)}")
    return 0


def cmd_validate(arg: str) -> int:
    workout, _ = _load(arg)
    if workout is None:
        return 1
    n_jobs = sum(len(s.jobs) for s in workout.stages)
    print(success(f"✅ VÁLIDO: {workout.name}  ({len(workout.stages)} stages, {n_jobs} jobs)"))
    return 0


def cmd_preview(arg: str, full: bool = False) -> int:
    workout, _ = _load(arg)
    if workout is None:
        return 1
    print(success("✅ Workout válido (v2).\n"))
    print(format_workout_v2_full(workout) if full else format_workout_v2_summary(workout))
    return 0


def cmd_run(arg: str) -> int:
    workout, path = _load(arg)
    if workout is None:
        return 1
    print(success(f"✅ {workout.name} — listo para ejecutar.\n"))
    print(format_workout_v2_summary(workout))
    print()
    run_workout_v2_interactive(workout, source_path=path)
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

    sub.add_parser("list", help="Lista los workouts disponibles.")
    sub.add_parser("stats", aliases=["stats-v2"], help="Estadísticas de tus sesiones.")

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
        if cmd == "list":
            return cmd_list()
        if cmd in ("stats", "stats-v2"):
            return cmd_stats()
        parser.print_help()
        return 0
    except (KeyboardInterrupt, EOFError):
        print(info("\nCancelado."))
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
