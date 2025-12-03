# src/domain/models/job.py

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Callable, List, Optional
import logging

from ..workout_errors import JobValidationError, ExerciseValidationError
from .exercise import Exercise

log = logging.getLogger(__name__)


class JobMode(Enum):
    CUSTOM_SETS = "custom_sets"
    TABATA = "TABATA"
    # futuro: EMOM, AMRAP, SUPER_SETS, etc.

    @property
    def description(self) -> str:
        if self is JobMode.CUSTOM_SETS:
            return "Custom sets: fixed list of exercises per round."
        if self is JobMode.TABATA:
            return "Tabata: fixed rounds of work/rest intervals."
        return self.value


@dataclass(frozen=True)
class Job:
    """
    Static definition of a job (block of work) inside a stage.
    """
    name: str
    mode: JobMode
    rounds: int
    exercises: List[Exercise] = field(default_factory=list)

    description: Optional[str] = None
    rest_between_exercises_in_seconds: Optional[int] = None
    rest_between_rounds_in_seconds: Optional[int] = None
    work_time_in_seconds: Optional[int] = None
    work_time_in_minutes: Optional[int] = None
    cadence: Optional[str] = None
    eccentric_neg: Optional[bool] = None
    isometric_hold: Optional[bool] = None
    rest_time_in_seconds: Optional[int] = None

    # ------------ helpers genéricos de validación ------------

    @staticmethod
    def _require_str(data: Mapping[str, Any], field: str) -> str:
        value = data.get(field)
        if not isinstance(value, str):
            raise JobValidationError(f"Field {field!r} must be a non-empty string.")
        if not value.strip():
            raise JobValidationError(f"Field {field!r} must not be empty.")
        return value

    @staticmethod
    def _optional_str(data: Mapping[str, Any], field: str) -> str | None:
        value = data.get(field)
        if value is None:
            return None
        if not isinstance(value, str):
            raise JobValidationError(f"Field {field!r} must be a string if present.")
        return value

    # ------------ CUSTOM_SETS ------------

    @classmethod
    def from_dict_custom_sets(cls, data: Mapping[str, Any]) -> "Job":
        """
        Build a Job in CUSTOM_SETS mode from a raw dict (YAML-parsed).
        """
        if not isinstance(data, Mapping):
            raise JobValidationError(
                f"Job must be a mapping/dict, got {type(data).__name__}"
            )

        log.debug("Parsing CUSTOM_SETS job from dict: NAME=%r", data.get("NAME"))

        # NAME
        try:
            raw_name = data["NAME"]
        except KeyError as exc:
            raise JobValidationError("Job is missing required field 'NAME'") from exc

        if not isinstance(raw_name, str) or not raw_name.strip():
            raise JobValidationError("Job 'NAME' must be a non-empty string")
        name = raw_name.strip()

        # MODE
        try:
            raw_mode = data["MODE"]
        except KeyError as exc:
            raise JobValidationError(
                f"Job '{name}' is missing required field 'MODE'"
            ) from exc

        if not isinstance(raw_mode, str):
            raise JobValidationError(
                f"Job '{name}' field 'MODE' must be a string"
            )

        if raw_mode != JobMode.CUSTOM_SETS.value:
            raise JobValidationError(
                f"Job '{name}' has unsupported MODE '{raw_mode}', "
                f"expected '{JobMode.CUSTOM_SETS.value}' for custom_sets schema"
            )

        mode = JobMode.CUSTOM_SETS

        # Rounds
        try:
            raw_rounds = data["Rounds"]
        except KeyError as exc:
            raise JobValidationError(
                f"Job '{name}' is missing required field 'Rounds'"
            ) from exc

        if not isinstance(raw_rounds, int):
            raise JobValidationError(
                f"Job '{name}' field 'Rounds' must be an integer"
            )

        if raw_rounds <= 0:
            raise JobValidationError(
                f"Job '{name}' field 'Rounds' must be > 0, got {raw_rounds}"
            )

        rounds = raw_rounds

        # EXERCISES
        try:
            raw_exercises = data["EXERCISES"]
        except KeyError as exc:
            raise JobValidationError(
                f"Job '{name}' is missing required field 'EXERCISES'"
            ) from exc

        if not isinstance(raw_exercises, list):
            raise JobValidationError(
                f"Job '{name}' field 'EXERCISES' must be a list"
            )

        if not raw_exercises:
            raise JobValidationError(
                f"Job '{name}' field 'EXERCISES' must contain at least one item"
            )

        log.debug("Job %r (mode=%s): parsing %d exercises", name, mode.value, len(raw_exercises))

        exercises: List[Exercise] = []
        for idx, ex_data in enumerate(raw_exercises):
            try:
                ex = Exercise.from_dict(ex_data)
            except ExerciseValidationError as exc:
                raise JobValidationError(
                    f"Job '{name}' has invalid exercise at index {idx}: {exc}"
                ) from exc
            exercises.append(ex)

        # Optional fields
        raw_description = data.get("description")
        if raw_description is not None and not isinstance(raw_description, str):
            raise JobValidationError(
                f"Job '{name}' field 'description' must be a string if provided"
            )

        raw_rest_between_ex = data.get("Rest_between_exercises_in_seconds")
        if raw_rest_between_ex is not None and not isinstance(raw_rest_between_ex, int):
            raise JobValidationError(
                f"Job '{name}' field 'Rest_between_exercises_in_seconds' "
                f"must be an integer if provided"
            )

        raw_rest_between_rounds = data.get("Rest_between_rounds_in_seconds")
        if raw_rest_between_rounds is not None and not isinstance(
            raw_rest_between_rounds, int
        ):
            raise JobValidationError(
                f"Job '{name}' field 'Rest_between_rounds_in_seconds' "
                f"must be an integer if provided"
            )

        raw_work_time_seconds = data.get("work_time_in_seconds")
        if raw_work_time_seconds is not None and not isinstance(
            raw_work_time_seconds, int
        ):
            raise JobValidationError(
                f"Job '{name}' field 'work_time_in_seconds' "
                f"must be an integer if provided"
            )

        raw_work_time_minutes = data.get("work_time_in_minutes")
        if raw_work_time_minutes is not None and not isinstance(
            raw_work_time_minutes, int
        ):
            raise JobValidationError(
                f"Job '{name}' field 'work_time_in_minutes' "
                f"must be an integer if provided"
            )

        raw_cadence = data.get("cadence")
        if raw_cadence is not None and not isinstance(raw_cadence, str):
            raise JobValidationError(
                f"Job '{name}' field 'cadence' must be a string if provided"
            )

        raw_eccentric_neg = data.get("Eccentric (NEG)")
        if raw_eccentric_neg is not None and not isinstance(raw_eccentric_neg, bool):
            raise JobValidationError(
                f"Job '{name}' field 'Eccentric (NEG)' must be a boolean if provided"
            )

        raw_isometric_hold = data.get("isometric (HOLD)")
        if raw_isometric_hold is not None and not isinstance(raw_isometric_hold, bool):
            raise JobValidationError(
                f"Job '{name}' field 'isometric (HOLD)' must be a boolean if provided"
            )

        log.debug(
            "Job %r (CUSTOM_SETS) parsed: rounds=%d exercises=%d",
            name,
            rounds,
            len(exercises),
        )

        return cls(
            name=name,
            mode=mode,
            rounds=rounds,
            exercises=exercises,
            description=raw_description,
            rest_between_exercises_in_seconds=raw_rest_between_ex,
            rest_between_rounds_in_seconds=raw_rest_between_rounds,
            work_time_in_seconds=raw_work_time_seconds,
            work_time_in_minutes=raw_work_time_minutes,
            cadence=raw_cadence,
            eccentric_neg=raw_eccentric_neg,
            isometric_hold=raw_isometric_hold,
        )

    # ------------ TABATA ------------

    @classmethod
    def from_dict_tabata(cls, data: Mapping[str, Any]) -> "Job":
        """
        Build a TABATA job from a raw dict.
        """
        if not isinstance(data, Mapping):
            raise JobValidationError("Tabata job payload must be a mapping/object.")

        log.debug("Parsing TABATA job from dict: NAME=%r", data.get("NAME"))

        mode_raw = cls._require_str(data, "MODE")
        if mode_raw != JobMode.TABATA.value:
            raise JobValidationError(
                f"Expected MODE 'TABATA' for Tabata job, got {mode_raw!r}"
            )

        name = cls._require_str(data, "NAME")
        description = cls._optional_str(data, "description")

        # rounds
        rounds = data.get("rounds", 8)
        if not isinstance(rounds, int) or rounds <= 0:
            raise JobValidationError("Field 'rounds' must be a positive integer.")

        # work_time_in_seconds
        work_time = data.get("work_time_in_seconds", 20)
        if not isinstance(work_time, int) or work_time <= 0:
            raise JobValidationError(
                "Field 'work_time_in_seconds' must be a positive integer."
            )

        # rest_time_in_seconds
        rest_time = data.get("rest_time_in_seconds", 10)
        if not isinstance(rest_time, int) or rest_time <= 0:
            raise JobValidationError(
                "Field 'rest_time_in_seconds' must be a positive integer."
            )

        log.debug(
            "Job %r (TABATA): rounds=%d work=%ds rest=%ds",
            name,
            rounds,
            work_time,
            rest_time,
        )

        # EXERCISES
        raw_exercises = data.get("EXERCISES")
        if not isinstance(raw_exercises, list):
            raise JobValidationError("Field 'EXERCISES' must be a list.")
        if not raw_exercises:
            raise JobValidationError("Field 'EXERCISES' must not be empty.")

        log.debug("Job %r (TABATA): parsing %d exercises", name, len(raw_exercises))

        exercises: list[Exercise] = []
        for idx, ex_data in enumerate(raw_exercises):
            if not isinstance(ex_data, Mapping):
                raise JobValidationError(
                    f"Exercise at index {idx} must be an object/dict."
                )
            try:
                ex = Exercise.from_dict(ex_data)
            except ExerciseValidationError as exc:
                raise JobValidationError(
                    f"Invalid exercise at index {idx}: {exc}"
                ) from exc

            # Regla específica de TABATA: reps obligatorio y > 0
            if ex.reps is None or not isinstance(ex.reps, int) or ex.reps <= 0:
                raise JobValidationError(
                    f"Tabata exercise at index {idx} must define a positive 'reps' value."
                )

            exercises.append(ex)

        log.debug(
            "Job %r (TABATA) parsed: rounds=%d exercises=%d",
            name,
            rounds,
            len(exercises),
        )

        return cls(
            name=name,
            mode=JobMode.TABATA,
            rounds=rounds,
            exercises=exercises,
            description=description,
            work_time_in_seconds=work_time,
            rest_time_in_seconds=rest_time,
        )


class JobFactory:
    """
    Central registry mapping JobMode -> parser function (dict -> Job).
    """

    _parsers: dict[JobMode, Callable[[Mapping[str, Any]], Job]] = {}

    @classmethod
    def register(
        cls,
        mode: JobMode,
        parser: Callable[[Mapping[str, Any]], Job],
    ) -> None:
        log.debug("Registering job parser for mode=%s: %s", mode.value, parser.__name__)
        cls._parsers[mode] = parser

    @classmethod
    def get_parser(
        cls,
        mode_value: str,
    ) -> Callable[[Mapping[str, Any]], Job] | None:
        """
        Return the parser function for a given MODE string, or None if unsupported.
        """
        for mode, parser in cls._parsers.items():
            if mode.value == mode_value:
                return parser
        return None


# Registrar los modos soportados actualmente
JobFactory.register(JobMode.CUSTOM_SETS, Job.from_dict_custom_sets)
JobFactory.register(JobMode.TABATA, Job.from_dict_tabata)