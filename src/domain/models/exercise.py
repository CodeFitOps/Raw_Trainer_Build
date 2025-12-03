# src/domain/models/exercise.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any, Mapping
import logging

from ..workout_errors import ExerciseValidationError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Exercise:
    """
    Static definition of a single exercise within a job.
    """
    name: str
    reps: Optional[int] = None
    work_time_in_seconds: Optional[int] = None
    weight: Optional[int] = None
    help: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Exercise":
        """
        Build an Exercise from a raw dict (YAML-parsed).
        """
        if not isinstance(data, Mapping):
            raise ExerciseValidationError(
                f"Exercise must be a mapping/dict, got {type(data).__name__}"
            )

        log.debug("Parsing exercise from dict: NAME=%r", data.get("NAME"))

        # NAME
        try:
            raw_name = data["NAME"]
        except KeyError as exc:
            raise ExerciseValidationError("Exercise is missing required field 'NAME'") from exc

        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ExerciseValidationError("Exercise 'NAME' must be a non-empty string")

        # reps
        raw_reps = data.get("reps")
        if raw_reps is not None and not isinstance(raw_reps, int):
            raise ExerciseValidationError("Exercise 'reps' must be an integer if provided")

        # work_time_in_seconds
        raw_work_time = data.get("work_time_in_seconds")
        if raw_work_time is not None and not isinstance(raw_work_time, int):
            raise ExerciseValidationError(
                "Exercise 'work_time_in_seconds' must be an integer if provided"
            )

        # anyOf: reps OR work_time_in_seconds
        if raw_reps is None and raw_work_time is None:
            raise ExerciseValidationError(
                "Exercise must define at least one of 'reps' or 'work_time_in_seconds'"
            )

        # weight
        raw_weight = data.get("weight")
        if raw_weight is not None and not isinstance(raw_weight, int):
            raise ExerciseValidationError("Exercise 'weight' must be an integer if provided")

        # help
        raw_help = data.get("help")
        if raw_help is not None and not isinstance(raw_help, str):
            raise ExerciseValidationError("Exercise 'help' must be a string if provided")

        log.debug(
            "Exercise parsed: name=%r reps=%r work_time_in_seconds=%r weight=%r",
            raw_name,
            raw_reps,
            raw_work_time,
            raw_weight,
        )

        return cls(
            name=raw_name.strip(),
            reps=raw_reps,
            work_time_in_seconds=raw_work_time,
            weight=raw_weight,
            help=raw_help,
        )