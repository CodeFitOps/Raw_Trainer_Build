#!/usr/bin/env python
"""
Validate a workout YAML file using the Python domain model.

Usage:

    python internal_tools/validate_workout_domain.py path/to/workout.yaml
"""
#!/usr/bin/env python
"""
Validate a workout YAML file using the Python domain model.
"""

import argparse
from pathlib import Path
import sys

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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a workout YAML using Workout.from_dict"
    )
    parser.add_argument("workout_file", type=Path,
                        help="Path to workout YAML file")
    args = parser.parse_args()

    if yaml is None:
        print("ERROR: pyyaml must be installed to use this script.",
              file=sys.stderr)
        return 1

    try:
        raw_text = args.workout_file.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: cannot read {args.workout_file}: {exc}",
              file=sys.stderr)
        return 1

    try:
        data = yaml.safe_load(raw_text)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: YAML parse error in {args.workout_file}: {exc}",
              file=sys.stderr)
        return 1

    print(f"Loaded YAML from {args.workout_file}")
    # Aquí entra en juego el dominio:
    try:
        workout = Workout.from_dict(data)
    except WorkoutError as exc:
        print("❌ Workout is INVALID according to domain model.")
        print(f"   Error: {exc}")
        return 2
    except Exception as exc:  # por si se cuela algo inesperado
        print("❌ Unexpected error while building Workout:", file=sys.stderr)
        print(f"   {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3

    # Si llega aquí, el dominio lo considera válido
    print("✅ Workout is VALID according to domain model.")
    print(f"   Name: {workout.name!r}")
    print(f"   Stages: {len(workout.stages)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())