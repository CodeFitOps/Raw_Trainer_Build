#!/usr/bin/env python
"""
Validate a workout YAML file using the Python domain model.

Usage:

    python internal_tools/validate_workout_domain.py path/to/workout.yaml
"""

from __future__ import annotations

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

    try:
        raw_text = args.workout_file.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: cannot read {args.workout_file}: {exc}", file=sys.stderr)
        log.error("Cannot read %s: %s", args.workout_file, exc)
        return 1

    try:
        data = yaml.safe_load(raw_text)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: YAML parse error in {args.workout_file}: {exc}", file=sys.stderr)
        log.error("YAML parse error in %s: %s", args.workout_file, exc)
        return 1

    print(f"Loaded YAML from {args.workout_file}")
    log.info("Loaded YAML from %s", args.workout_file)

    # Aquí entra en juego el dominio:
    try:
        workout = Workout.from_dict(data)
    except WorkoutError as exc:
        print("❌ Workout is INVALID according to domain model.")
        print(f"   Error: {exc}")
        log.error("Workout is INVALID according to domain model: %s", exc)
        return 2
    except Exception as exc:  # por si se cuela algo inesperado
        print("❌ Unexpected error during Workout validation.", file=sys.stderr)
        print(f"   {type(exc).__name__}: {exc}", file=sys.stderr)
        log.exception("Unexpected error while building Workout")
        return 3

    # Si llega aquí, el dominio lo considera válido
    print("✅ Workout is VALID according to domain model.")
    print(f"   Name: {workout.name!r}")
    print(f"   Stages: {len(workout.stages)}")

    log.info(
        "Workout is VALID according to domain model: name=%r stages=%d",
        workout.name,
        len(workout.stages),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())