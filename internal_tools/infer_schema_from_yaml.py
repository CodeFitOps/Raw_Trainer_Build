#!/usr/bin/env python
"""
infer_schema_from_yaml.py

Bootstrap a JSON Schema from one or more YAML files.

Usage (example):

    python internal_tools/infer_schema_from_yaml.py \
        internal_tools/examples/job_tabata_example.yaml \
        --output internal_tools/schemas/job.tabata.schema.json
"""

import argparse
import json
from pathlib import Path
import sys

try:
    import yaml  # type: ignore
    from genson import SchemaBuilder  # type: ignore
except ImportError:
    yaml = None
    SchemaBuilder = None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Infer a JSON Schema from one or more YAML files."
    )
    parser.add_argument("yaml_files", nargs="+", type=Path,
                        help="YAML files to infer schema from")
    parser.add_argument("--output", "-o", type=Path, required=True,
                        help="Path to write the inferred JSON Schema")
    args = parser.parse_args()

    if yaml is None or SchemaBuilder is None:
        print("ERROR: pyyaml and genson must be installed "
              "to use this script.", file=sys.stderr)
        return 1

    builder = SchemaBuilder()
    builder.add_schema({"type": "object"})

    for path in args.yaml_files:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: Failed to read/parse YAML {path}: {exc}",
                  file=sys.stderr)
            return 1
        builder.add_object(raw)

    schema = builder.to_schema()
    args.output.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print(f"Schema written to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())