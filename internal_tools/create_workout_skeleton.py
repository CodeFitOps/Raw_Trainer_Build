#!/usr/bin/env python
"""
create_workout_skeleton.py

Generate a minimal workout YAML skeleton.

Usage:

    python internal_tools/create_workout_skeleton.py \
        --name "My Workout" \
        --description "Short description" \
        --output workout_my_new.yaml
"""

import argparse
from pathlib import Path


TEMPLATE = """NAME: "{name}"
description: "{description}"
STAGES: []
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a minimal workout YAML skeleton."
    )
    parser.add_argument("--name", "-n", default="New Workout",
                        help="Workout name to put in the skeleton")
    parser.add_argument("--description", "-d", default="",
                        help="Workout description to put in the skeleton")
    parser.add_argument("--output", "-o", type=Path,
                        default=Path("workout_skeleton.yaml"),
                        help="Output YAML file")
    args = parser.parse_args()

    content = TEMPLATE.format(
        name=args.name,
        description=args.description.replace('"', '\\"'),
    )
    args.output.write_text(content, encoding="utf-8")
    print(f"Workout skeleton written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())