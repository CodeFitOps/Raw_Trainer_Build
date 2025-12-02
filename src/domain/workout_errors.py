"""
Custom exception hierarchy for workout-related validation.

We keep this in a separate module so it can be reused by:
- workout_model (from_dict builders)
- YAML loaders
- Coach / runtime logic (if needed later)
"""


class WorkoutError(Exception):
    """Base class for all workout-related errors."""


# --- Validation / parsing errors ---


class WorkoutValidationError(WorkoutError):
    """
    Base class for errors that occur while validating or
    constructing workout objects from raw data (dict/YAML).
    """


class WorkoutTopLevelValidationError(WorkoutValidationError):
    """Errors related to the top-level workout structure (NAME, STAGES, etc.)."""


class StageValidationError(WorkoutValidationError):
    """Errors related to a single stage definition."""


class JobValidationError(WorkoutValidationError):
    """Errors related to a single job definition."""


class ExerciseValidationError(WorkoutValidationError):
    """Errors related to a single exercise definition."""