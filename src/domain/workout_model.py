from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Any, Mapping

from .workout_errors import(
    WorkoutError,
    WorkoutValidationError,
    WorkoutTopLevelValidationError,
    StageValidationError,
    JobValidationError,
    ExerciseValidationError,
)


class JobMode(Enum):
    CUSTOM_SETS = "custom_sets"
    TABATA = "TABATA"
    # en el futuro: EMOM, AMRAP, etc.

    @property
    def description(self) -> str:
        if self is JobMode.CUSTOM_SETS:
            return "Custom sets: fixed list of exercises per round."
        if self is JobMode.TABATA:
            return "Tabata: fixed rounds of 20s work / 10s rest (or custom timing)."
        return self.value


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

        return cls(
            name=raw_name.strip(),
            reps=raw_reps,
            work_time_in_seconds=raw_work_time,
            weight=raw_weight,
            help=raw_help,
        )


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
    # usado por TABATA
    rest_time_in_seconds: Optional[int] = None

    @classmethod
    def from_dict_custom_sets(cls, data: Mapping[str, Any]) -> "Job":
        """
        Build a Job in CUSTOM_SETS mode from a raw dict (YAML-parsed).
        """
        if not isinstance(data, Mapping):
            raise JobValidationError(
                f"Job must be a mapping/dict, got {type(data).__name__}"
            )

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

    @classmethod
    def from_dict_tabata(cls, data: Mapping[str, Any]) -> "Job":
        """
        Build a TABATA job from a raw dict.

        Rules (alineado con job.tabata.schema.json):
        - MODE must be exactly "TABATA".
        - Required: NAME, MODE, EXERCISES.
        - rounds: optional, positive int, default 8.
        - work_time_in_seconds: optional, positive int, default 20.
        - rest_time_in_seconds: optional, positive int, default 10.
        - EXERCISES: non-empty list.
          Each exercise must have NAME (string) and reps (positive int).
          weight is optional.
        """
        if not isinstance(data, Mapping):
            raise JobValidationError("Tabata job payload must be a mapping/object.")

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

        # EXERCISES
        raw_exercises = data.get("EXERCISES")
        if not isinstance(raw_exercises, list):
            raise JobValidationError("Field 'EXERCISES' must be a list.")
        if not raw_exercises:
            raise JobValidationError("Field 'EXERCISES' must not be empty.")

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

        return cls(
            name=name,
            mode=JobMode.TABATA,
            rounds=rounds,
            exercises=exercises,
            description=description,
            work_time_in_seconds=work_time,
            rest_time_in_seconds=rest_time,
        )


@dataclass(frozen=True)
class Stage:
    name: str
    jobs: List[Job] = field(default_factory=list)
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Stage":
        """
        Build a Stage from a raw dict (YAML-parsed).

        Expected keys:

          Required:
            - NAME (str)
            - JOBS (non-empty list of job dicts)

          Optional:
            - description (str)
        """
        if not isinstance(data, Mapping):
            raise StageValidationError(
                f"Stage must be a mapping/dict, got {type(data).__name__}"
            )

        # NAME (required)
        try:
            raw_name = data["NAME"]
        except KeyError as exc:
            raise StageValidationError("Stage is missing required field 'NAME'") from exc

        if not isinstance(raw_name, str) or not raw_name.strip():
            raise StageValidationError("Stage 'NAME' must be a non-empty string")
        name = raw_name.strip()

        # JOBS (required)
        try:
            raw_jobs = data["JOBS"]
        except KeyError as exc:
            raise StageValidationError(
                f"Stage '{name}' is missing required field 'JOBS'"
            ) from exc

        if not isinstance(raw_jobs, list):
            raise StageValidationError(
                f"Stage '{name}' field 'JOBS' must be a list"
            )

        if not raw_jobs:
            raise StageValidationError(
                f"Stage '{name}' field 'JOBS' must contain at least one item"
            )

        jobs: List[Job] = []
        for idx, job_data in enumerate(raw_jobs):
            if not isinstance(job_data, Mapping):
                raise StageValidationError(
                    f"Stage '{name}' has job at index {idx} that is not a mapping/dict "
                    f"(got {type(job_data).__name__})"
                )

            raw_mode = job_data.get("MODE")
            if raw_mode is None:
                raise StageValidationError(
                    f"Stage '{name}' has job at index {idx} missing required field 'MODE'"
                )

            if not isinstance(raw_mode, str):
                raise StageValidationError(
                    f"Stage '{name}' has job at index {idx} with 'MODE' that must be a string"
                )

            if raw_mode == JobMode.CUSTOM_SETS.value:
                try:
                    job = Job.from_dict_custom_sets(job_data)
                except JobValidationError as exc:
                    raise StageValidationError(
                        f"Stage '{name}' has invalid job at index {idx}: {exc}"
                    ) from exc
            elif raw_mode == JobMode.TABATA.value:
                try:
                    job = Job.from_dict_tabata(job_data)
                except JobValidationError as exc:
                    raise StageValidationError(
                        f"Stage '{name}' has invalid TABATA job at index {idx}: {exc}"
                    ) from exc
            else:
                raise StageValidationError(
                    f"Stage '{name}' has job at index {idx} with unsupported MODE '{raw_mode}'"
                )

            jobs.append(job)

        # description (optional)
        raw_description = data.get("description")
        if raw_description is not None and not isinstance(raw_description, str):
            raise StageValidationError(
                f"Stage '{name}' field 'description' must be a string if provided"
            )

        return cls(
            name=name,
            jobs=jobs,
            description=raw_description,
        )


@dataclass(frozen=True)
class Workout:
    name: str
    stages: List[Stage] = field(default_factory=list)
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Workout":
        """
        Build a Workout from a raw dict (YAML-parsed).

        Expected keys:

          Required:
            - NAME   (str)
            - STAGES (non-empty list of stage dicts)

          Optional:
            - description (str)
        """
        if not isinstance(data, Mapping):
            raise WorkoutTopLevelValidationError(
                f"Workout must be a mapping/dict, got {type(data).__name__}"
            )

        # NAME (required)
        try:
            raw_name = data["NAME"]
        except KeyError as exc:
            raise WorkoutTopLevelValidationError(
                "Workout is missing required field 'NAME'"
            ) from exc

        if not isinstance(raw_name, str) or not raw_name.strip():
            raise WorkoutTopLevelValidationError(
                "Workout 'NAME' must be a non-empty string"
            )
        name = raw_name.strip()

        # STAGES (required)
        try:
            raw_stages = data["STAGES"]
        except KeyError as exc:
            raise WorkoutTopLevelValidationError(
                f"Workout '{name}' is missing required field 'STAGES'"
            ) from exc

        if not isinstance(raw_stages, list):
            raise WorkoutTopLevelValidationError(
                f"Workout '{name}' field 'STAGES' must be a list"
            )

        if not raw_stages:
            raise WorkoutTopLevelValidationError(
                f"Workout '{name}' field 'STAGES' must contain at least one item"
            )

        stages: List[Stage] = []
        for idx, stage_data in enumerate(raw_stages):
            if not isinstance(stage_data, Mapping):
                raise WorkoutTopLevelValidationError(
                    f"Workout '{name}' has stage at index {idx} that is not a mapping/dict "
                    f"(got {type(stage_data).__name__})"
                )

            try:
                stage = Stage.from_dict(stage_data)
            except StageValidationError as exc:
                raise WorkoutTopLevelValidationError(
                    f"Workout '{name}' has invalid stage at index {idx}: {exc}"
                ) from exc

            stages.append(stage)

        # description (optional)
        raw_description = data.get("description")
        if raw_description is not None and not isinstance(raw_description, str):
            raise WorkoutTopLevelValidationError(
                f"Workout '{name}' field 'description' must be a string if provided"
            )

        return cls(
            name=name,
            stages=stages,
            description=raw_description,
        )