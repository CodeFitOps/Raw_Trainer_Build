# src/domain_v2/model.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class ExerciseV2:
    name: str
    reps: Optional[int] = None
    work_time_in_seconds: Optional[int] = None
    weight: Optional[float] = None
    notes: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

@dataclass
class JobV2:
    name: str
    mode: str
    description: Optional[str] = None

    rounds: Optional[int] = None
    work_time_in_seconds: Optional[int] = None
    work_time_in_minutes: Optional[int] = None

    rest_time_in_seconds: Optional[int] = None
    rest_between_exercises_in_seconds: Optional[int] = None
    rest_between_rounds_in_seconds: Optional[int] = None

    cadence: Optional[str] = None
    eccentric_neg: Optional[bool] = None
    isometric_hold: Optional[bool] = None

    exercises: List[ExerciseV2] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

@dataclass
class StageV2:
    name: str
    description: Optional[str] = None
    jobs: List[JobV2] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

@dataclass
class WorkoutV2:
    name: str
    description: Optional[str] = None
    stages: List[StageV2] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)