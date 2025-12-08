# src/domain_v2/schema_loader.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List
import yaml
from jsonschema import Draft7Validator
from .model import WorkoutV2, StageV2, JobV2, ExerciseV2


class SchemaValidationError(Exception):
    pass

def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_workout_yaml_with_schema(yaml_path: Path, schema_path: Path) -> Dict[str, Any]:
    data = _load_yaml(yaml_path)
    schema = _load_json(schema_path)
    validator = Draft7Validator(schema)

    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        msgs: List[str] = []
        for err in errors:
            location = ".".join(str(p) for p in err.path)
            msgs.append(f"{location}: {err.message}")
        raise SchemaValidationError(
            f"{yaml_path} is invalid according to workout schema:\n" + "\n".join(msgs)
        )

    return data


def build_workout_v2_from_dict(data: Dict[str, Any]) -> WorkoutV2:
    stages: list[StageV2] = []

    for stage_dict in data.get("STAGES", []):
        jobs: list[JobV2] = []

        for job_dict in stage_dict.get("JOBS", []):
            exercises: list[ExerciseV2] = []

            for ex_dict in job_dict.get("EXERCISES", []):
                exercises.append(
                    ExerciseV2(
                        name=(ex_dict.get("NAME") or "").strip(),
                        reps=ex_dict.get("reps"),
                        work_time_in_seconds=ex_dict.get("work_time_in_seconds"),
                        weight=ex_dict.get("weight"),
                        notes=(
                            ex_dict.get("notes")
                            or ex_dict.get("description")
                            or ex_dict.get("DESCRIPTION")
                        ),
                        raw=ex_dict,
                    )
                )

            jobs.append(
                JobV2(
                    name=(job_dict.get("NAME") or "").strip(),
                    mode=str(job_dict.get("MODE")).strip(),
                    description=job_dict.get("description")
                    or job_dict.get("Description"),
                    rounds=job_dict.get("Rounds") or job_dict.get("rounds"),
                    work_time_in_seconds=job_dict.get("work_time_in_seconds"),
                    work_time_in_minutes=job_dict.get("work_time_in_minutes"),
                    rest_time_in_seconds=job_dict.get("rest_time_in_seconds"),
                    rest_between_exercises_in_seconds=(
                        job_dict.get("Rest_between_exercises_in_seconds")
                        or job_dict.get("rest_between_exercises_in_seconds")
                    ),
                    rest_between_rounds_in_seconds=(
                        job_dict.get("Rest_between_rounds_in_seconds")
                        or job_dict.get("rest_between_rounds_in_seconds")
                    ),
                    cadence=job_dict.get("cadence") or job_dict.get("Cadence"),
                    eccentric_neg=job_dict.get("Eccentric (NEG)"),
                    isometric_hold=(
                        job_dict.get("isometric (HOLD)")
                        or job_dict.get("Isometric (HOLD)")
                    ),
                    exercises=exercises,
                    raw=job_dict,
                )
            )

        stages.append(
            StageV2(
                name=(stage_dict.get("NAME") or "").strip(),
                description=stage_dict.get("Description")
                or stage_dict.get("description"),
                jobs=jobs,
                raw=stage_dict,
            )
        )

    return WorkoutV2(
        name=(data.get("NAME") or "").strip(),
        description=data.get("Description") or data.get("description"),
        stages=stages,
        raw=data,
    )


def load_workout_v2(yaml_path: Path, schema_path: Path) -> WorkoutV2:
    data = validate_workout_yaml_with_schema(yaml_path, schema_path)
    return build_workout_v2_from_dict(data)