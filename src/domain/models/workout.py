# src/domain/models/workout.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Any, Mapping
import logging

from ..workout_errors import (
    WorkoutTopLevelValidationError,
    StageValidationError,
)
from .stage import Stage

log = logging.getLogger(__name__)


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

        log.debug("Parsing workout from dict: keys=%s", list(data.keys()))

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

        log.debug("Workout name parsed: %r", name)

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

        log.debug("Workout %r: parsing %d stages", name, len(raw_stages))

        stages: List[Stage] = []
        for idx, stage_data in enumerate(raw_stages):
            if not isinstance(stage_data, Mapping):
                raise WorkoutTopLevelValidationError(
                    f"Workout '{name}' has stage at index {idx} that is not a mapping/dict "
                    f"(got {type(stage_data).__name__})"
                )

            log.debug("Workout %r: parsing stage index=%d", name, idx)

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

        log.info(
            "Workout %r parsed successfully (stages=%d)",
            name,
            len(stages),
        )

        return cls(
            name=name,
            stages=stages,
            description=raw_description,
        )