#!/usr/bin/env python
"""
Validate a workout YAML file using the Python domain model.

Usage:

    python internal_tools/validate_workout_domain.py path/to/workout.yaml
"""

from __future__ import annotations
from src.application.workout_loader import load_workout_from_file, WorkoutLoadError
import argparse
from pathlib import Path
import sys
import logging

# --- make 'src' importable when running this script directly ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# --------------------------------------------------------------

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

from src.domain.workout_model import Workout
from src.domain.workout_errors import WorkoutError
from src.infrastructure.logging_setup import configure_logging

log = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a workout YAML using Workout.from_dict"
    )
    parser.add_argument(
        "workout_file",
        type=Path,
        help="Path to workout YAML file",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Also show technical logs (DEBUG) on console",
    )
    args = parser.parse_args()

    # 1) Configuramos logging global
    # - log_file: siempre logueamos a un fichero del proyecto
    # - enable_console_logs: solo si el user pide --debug
    log_file = PROJECT_ROOT / "logs" / "validate_workout_domain.log"
    configure_logging(
        level="DEBUG" if args.debug else None,
        log_file=log_file,
        enable_console_logs=args.debug,
    )

    # A partir de aquí, TODO lo que hagamos con log.* se va al fichero,
    # y si --debug está activo, también a la consola.

    if yaml is None:
        msg = "pyyaml must be installed to use this script."
        print(f"ERROR: {msg}", file=sys.stderr)
        log.error(msg)
        return 1

    print(f"Loaded YAML from {args.workout_file}")
    log.info("Loaded YAML from %s", args.workout_file)

    try:
        workout = load_workout_from_file(args.workout_file)
    except WorkoutLoadError as exc:
        print("❌ Workout is INVALID according to domain model.")
        print(f"   Error: {exc}")
        log.error("Workout load/validation failed: %s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())