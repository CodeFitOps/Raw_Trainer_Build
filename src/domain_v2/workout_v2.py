# src/domain_v2/workout_v2.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

class JobModeV2(str, Enum):
    CUSTOM_SETS = "CUSTOM"
    TABATA = "TABATA"
    EMOM = "EMOM"
    AMRAP = "AMRAP"
    FOR_TIME = "FT"
    EDT = "EDT"

    @classmethod
    def from_raw(cls, raw: str) -> "JobModeV2":
        s = str(raw).strip()
        lower = s.lower()
        if lower in {"custom_sets", "custom"}:
            return cls.CUSTOM_SETS
        if lower == "tabata":
            return cls.TABATA
        if lower == "emom":
            return cls.EMOM
        if lower == "amrap":
            return cls.AMRAP
        if lower == "for_time":
            return cls.FOR_TIME
        if lower == "edt":
            return cls.EDT
        # El schema ya debería haber filtrado esto
        raise ValueError(f"Unsupported MODE in v2: {raw!r}")

    def mode_label(self) -> str:
        """
        Etiqueta corta y consistente para mostrar el modo.
        """
        if self is JobModeV2.CUSTOM_SETS:
            return "CUSTOM"
        if self is JobModeV2.TABATA:
            return "TABATA"
        if self is JobModeV2.EMOM:
            return "EMOM"
        if self is JobModeV2.AMRAP:
            return "AMRAP"
        if self is JobModeV2.FOR_TIME:
            return "FT"
        if self is JobModeV2.EDT:
            return "EDT"
        return str(self.value)

    def mode_description(self) -> str:
        """
        Descripción fija del tipo de trabajo (MODO), no del job concreto.
        Esto es lo que mostraremos en el preview y en el runner antes de cada job.
        """
        if self is JobModeV2.CUSTOM_SETS:
            return (
                "CUSTOM: Bloques de ejercicios encadenados (supersets/giant sets). "
                "Se ejecutan las rondas definidas respetando descansos y/o cadencia."
            )
        if self is JobModeV2.TABATA:
            return (
                "TABATA: Intervalos cortos de alta intensidad, típicamente 20s ON / 10s OFF "
                "durante varias rondas."
            )
        if self is JobModeV2.EMOM:
            return (
                "EMOM: Every Minute On the Minute. Realiza el trabajo al inicio de cada minuto, "
                "descansando el resto del tiempo."
            )
        if self is JobModeV2.AMRAP:
            return (
                "AMRAP: As Many Rounds/Reps As Possible dentro de una ventana de tiempo fija."
            )
        if self is JobModeV2.FOR_TIME:
            return (
                "FOR TIME: Completa todas las reps indicadas lo más rápido posible. "
                "El tiempo total es la métrica principal."
            )
        if self is JobModeV2.EDT:
            return (
                "EDT: Escalating Density Training. Trabaja por bloques de tiempo fijos, "
                "acumulando el máximo volumen posible en uno o dos ejercicios."
            )
        return ""


# -------------------------------------------------------------------
# ExerciseV2
# -------------------------------------------------------------------


@dataclass
class ExerciseV2:
    name: str

    reps: Optional[int] = None
    work_time_in_seconds: Optional[int] = None
    weight: Optional[float] = None

    notes: Optional[str] = None
    help: Optional[str] = None

    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExerciseV2":
        """
        Construye ExerciseV2 asumiendo que `data` ya está validado por JSON Schema.
        No se hace validación fuerte, solo casting ligero y extracción de campos.
        """
        name = str(data.get("NAME") or data.get("name")).strip()

        reps = data.get("reps")
        work_time_in_seconds = data.get("work_time_in_seconds")
        weight = data.get("weight")

        if isinstance(weight, (int, float)):
            weight = float(weight)
        else:
            weight = None

        notes = None
        for key in ("notes", "note", "DESCRIPTION", "Description", "description"):
            val = data.get(key)
            if isinstance(val, str):
                notes = val.strip()
                break

        help_text = data.get("help")
        if isinstance(help_text, str):
            help_text = help_text.strip()
        else:
            help_text = None

        core_keys = {
            "NAME",
            "name",
            "reps",
            "work_time_in_seconds",
            "weight",
            "notes",
            "note",
            "DESCRIPTION",
            "Description",
            "description",
            "help",
        }
        extra = {k: v for k, v in data.items() if k not in core_keys}

        return cls(
            name=name,
            reps=reps,
            work_time_in_seconds=work_time_in_seconds,
            weight=weight,
            notes=notes,
            help=help_text,
            extra=extra,
        )


# -------------------------------------------------------------------
# JobV2
# -------------------------------------------------------------------


@dataclass
class JobV2:
    name: str
    mode: JobModeV2

    description: Optional[str] = None
    rounds: Optional[int] = None

    work_time_in_seconds: Optional[int] = None
    work_time_in_minutes: Optional[int] = None

    rest_time_in_seconds: Optional[int] = None
    rest_between_exercises_in_seconds: Optional[int] = None
    rest_between_rounds_in_seconds: Optional[int] = None

    cadence: Optional[str] = None
    eccentric_neg: bool = False
    isometric_hold: bool = False

    exercises: List[ExerciseV2] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobV2":
        """
        Construye JobV2 desde un dict validado por JSON Schema.

        Aquí no lanzamos errores "de usuario": si algo viene raro es bug,
        no input error (la validación ya se hizo antes).
        """
        name = str(data.get("NAME") or data.get("name")).strip()
        mode = JobModeV2.from_raw(str(data.get("MODE")))

        desc_raw = data.get("description") or data.get("Description")
        description = desc_raw.strip() if isinstance(desc_raw, str) else None

        rounds = data.get("Rounds") if "Rounds" in data else data.get("rounds")
        if isinstance(rounds, int) and rounds <= 0:
            rounds = None  # schema no debería permitirlo, fallback defensivo

        work_time_in_seconds = data.get("work_time_in_seconds")
        work_time_in_minutes = data.get("work_time_in_minutes")

        rest_time_in_seconds = data.get("rest_time_in_seconds")
        rest_between_exercises_in_seconds = (
            data.get("Rest_between_exercises_in_seconds")
            or data.get("rest_between_exercises_in_seconds")
        )
        rest_between_rounds_in_seconds = (
            data.get("Rest_between_rounds_in_seconds")
            or data.get("rest_between_rounds_in_seconds")
        )

        cad_raw = data.get("cadence") or data.get("Cadence")
        cadence = cad_raw.strip() if isinstance(cad_raw, str) else None

        en_raw = data.get("Eccentric (NEG)") or data.get("eccentric_neg")
        if isinstance(en_raw, bool):
            eccentric_neg = en_raw
        elif isinstance(en_raw, str):
            eccentric_neg = en_raw.strip().lower() in {"true", "yes", "1"}
        else:
            eccentric_neg = False

        ih_raw = (
            data.get("isometric (HOLD)")
            or data.get("Isometric (HOLD)")
            or data.get("isometric_hold")
        )
        if isinstance(ih_raw, bool):
            isometric_hold = ih_raw
        elif isinstance(ih_raw, str):
            isometric_hold = ih_raw.strip().lower() in {"true", "yes", "1"}
        else:
            isometric_hold = False

        exs_raw = (
            data.get("EXERCISES")
            or data.get("Exercises")
            or data.get("exercises")
            or []
        )
        exercises = [
            ExerciseV2.from_dict(ex_data)
            for ex_data in exs_raw
            if isinstance(ex_data, dict)
        ]

        core_keys = {
            "NAME",
            "name",
            "MODE",
            "description",
            "Description",
            "Rounds",
            "rounds",
            "work_time_in_seconds",
            "work_time_in_minutes",
            "rest_time_in_seconds",
            "Rest_between_exercises_in_seconds",
            "rest_between_exercises_in_seconds",
            "Rest_between_rounds_in_seconds",
            "rest_between_rounds_in_seconds",
            "cadence",
            "Cadence",
            "Eccentric (NEG)",
            "eccentric_neg",
            "isometric (HOLD)",
            "Isometric (HOLD)",
            "isometric_hold",
            "EXERCISES",
            "Exercises",
            "exercises",
        }
        extra = {k: v for k, v in data.items() if k not in core_keys}

        return cls(
            name=name,
            mode=mode,
            description=description,
            rounds=rounds,
            work_time_in_seconds=work_time_in_seconds,
            work_time_in_minutes=work_time_in_minutes,
            rest_time_in_seconds=rest_time_in_seconds,
            rest_between_exercises_in_seconds=rest_between_exercises_in_seconds,
            rest_between_rounds_in_seconds=rest_between_rounds_in_seconds,
            cadence=cadence,
            eccentric_neg=eccentric_neg,
            isometric_hold=isometric_hold,
            exercises=exercises,
            extra=extra,
        )


# -------------------------------------------------------------------
# StageV2
# -------------------------------------------------------------------


@dataclass
class StageV2:
    name: str
    description: Optional[str] = None
    jobs: List[JobV2] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StageV2":
        name = str(data.get("NAME") or data.get("name")).strip()

        desc_raw = data.get("Description") or data.get("description")
        description = desc_raw.strip() if isinstance(desc_raw, str) else None

        jobs_raw = data.get("JOBS") or data.get("jobs") or []
        jobs = [
            JobV2.from_dict(job_data)
            for job_data in jobs_raw
            if isinstance(job_data, dict)
        ]

        return cls(name=name, description=description, jobs=jobs)


# -------------------------------------------------------------------
# WorkoutV2
# -------------------------------------------------------------------


@dataclass
class WorkoutV2:
    name: str
    description: Optional[str] = None
    stages: List[StageV2] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkoutV2":
        """
        Construye WorkoutV2 desde el dict ya validado por JSON Schema.
        """
        name = str(data.get("NAME") or data.get("name")).strip()

        desc_raw = data.get("Description") or data.get("description")
        description = desc_raw.strip() if isinstance(desc_raw, str) else None

        stages_raw = data.get("STAGES") or data.get("stages") or []
        stages = [
            StageV2.from_dict(stage_data)
            for stage_data in stages_raw
            if isinstance(stage_data, dict)
        ]

        # Guardamos una copia del dict original por si hace falta en el futuro
        return cls(
            name=name,
            description=description,
            stages=stages,
            raw=dict(data),
        )