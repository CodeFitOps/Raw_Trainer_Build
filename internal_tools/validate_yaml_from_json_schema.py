#!/usr/bin/env python
"""
validate_yaml_from_json_schema.py

Validate a YAML file against a JSON Schema.

Usage:

    python internal_tools/validate_yaml_from_json_schema.py \
        --schema internal_tools/schemas/workout.schema.json \
        path/to/workout.yaml
"""

import argparse
import json
from pathlib import Path
import sys

try:
    import yaml  # type: ignore
    from jsonschema import Draft7Validator  # type: ignore
except ImportError:
    yaml = None
    Draft7Validator = None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a YAML file against a JSON Schema."
    )
    parser.add_argument("--schema", "-s", type=Path, required=True,
                        help="Path to JSON Schema file")
    parser.add_argument("yaml_file", type=Path,
                        help="YAML file to validate")
    args = parser.parse_args()

    if yaml is None or Draft7Validator is None:
        print("ERROR: pyyaml and jsonschema must be installed "
              "to use this script.", file=sys.stderr)
        return 1

    try:
        schema_data = json.loads(args.schema.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Failed to read/parse schema {args.schema}: {exc}",
              file=sys.stderr)
        return 1

    try:
        yaml_data = yaml.safe_load(args.yaml_file.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: Failed to read/parse YAML {args.yaml_file}: {exc}",
              file=sys.stderr)
        return 1

    validator = Draft7Validator(schema_data)
    errors = sorted(validator.iter_errors(yaml_data), key=lambda e: e.path)

    if not errors:
        print(f"OK: {args.yaml_file} is valid against {args.schema}")
        return 0

    print(f"INVALID: {args.yaml_file} does not match {args.schema}")
    for err in errors:
        path = ".".join(str(p) for p in err.path) or "<root>"
        print(f"  - At {path}: {err.message}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())