from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Any, Mapping, Callable
import logging
from .models import Exercise, Job, JobMode, JobFactory, Stage, Workout

from .workout_errors import(
    WorkoutError,
    WorkoutValidationError,
    WorkoutTopLevelValidationError,
    StageValidationError,
    JobValidationError,
    ExerciseValidationError,
)

log = logging.getLogger(__name__)

# Registrar los modos soportados actualmente
#JobFactory.register(JobMode.CUSTOM_SETS, Job.from_dict_custom_sets)
#JobFactory.register(JobMode.TABATA, Job.from_dict_tabata)
