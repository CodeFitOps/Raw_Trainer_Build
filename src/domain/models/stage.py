# src/domain/models/stage.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Any, Mapping
import logging

from ..workout_errors import StageValidationError, JobValidationError
from .job import JobFactory, Job

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Stage:
    name: str
    jobs: List[Job] = field(default_factory=list)
    description: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Stage":
        """
        Build a Stage from a raw dict (YAML-parsed).
        """
        if not isinstance(data, Mapping):
            raise StageValidationError(
                f"Stage must be a mapping/dict, got {type(data).__name__}"
            )

        log.debug("Parsing stage from dict: keys=%s", list(data.keys()))

        # NAME (required)
        try:
            raw_name = data["NAME"]
        except KeyError as exc:
            raise StageValidationError("Stage is missing required field 'NAME'") from exc

        if not isinstance(raw_name, str) or not raw_name.strip():
            raise StageValidationError("Stage 'NAME' must be a non-empty string")
        name = raw_name.strip()

        log.debug("Stage name parsed: %r", name)

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

        log.debug("Stage %r: parsing %d jobs", name, len(raw_jobs))

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
                    f"Stage '{name}' has job at index {idx} with 'MODE' needing string"
                )

            log.debug(
                "Stage %r: job index=%d MODE=%r",
                name,
                idx,
                raw_mode,
            )

            parser = JobFactory.get_parser(raw_mode)
            if parser is None:
                raise StageValidationError(
                    f"Stage '{name}' has job at index {idx} with unsupported MODE '{raw_mode}'"
                )

            try:
                job = parser(job_data)
            except JobValidationError as exc:
                raise StageValidationError(
                    f"Stage '{name}' has invalid job at index {idx}: {exc}"
                ) from exc

            jobs.append(job)

        # description (optional)
        raw_description = data.get("description")
        if raw_description is not None and not isinstance(raw_description, str):
            raise StageValidationError(
                f"Stage '{name}' field 'description' must be a string if provided"
            )

        log.debug(
            "Stage %r parsed successfully (jobs=%d)",
            name,
            len(jobs),
        )

        return cls(
            name=name,
            jobs=jobs,
            description=raw_description,
        )