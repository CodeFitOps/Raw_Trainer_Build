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
    LADDER = "LADDER"
    INTERVAL = "INTERVAL"
    CARRY = "CARRY"

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
        if lower in {"super_sets", "supersets"}:
            return cls.CUSTOM_SETS
        if lower == "ladder":
            return cls.LADDER
        if lower in {"interval", "hiit"}:
            return cls.INTERVAL
        if lower in {"carry", "hold", "carries", "loaded_carry", "farmers_walk"}:
            return cls.CARRY
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
        if self is JobModeV2.LADDER:
            return "LADDER"
        if self is JobModeV2.INTERVAL:
            return "INTERVAL"
        if self is JobModeV2.CARRY:
            return "CARRY/HOLD"
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
        if self is JobModeV2.LADDER:
            return (
                "LADDER: Escalera de repeticiones. Sube o baja las reps en cada ronda "
                "segun el incremento definido (ascendente o descendente)."
            )
        if self is JobModeV2.INTERVAL:
            return (
                "INTERVAL: Bloques de trabajo/descanso repetidos (HIIT). "
                "Tabata es un preset (20s/10s x8)."
            )
        if self is JobModeV2.CARRY:
            return (
                "CARRY/HOLD: Acarreos y sostenidos cargados. La prescripción se "
                "mide por distancia (m) o por tiempo (s), normalmente con peso "
                "(farmer's walk, yoke, sled, plancha, dead hang)."
            )
        return ""


# -------------------------------------------------------------------
# SetPrescriptionV2
# -------------------------------------------------------------------


@dataclass
class SetPrescriptionV2:
    """Prescripción de UNA serie concreta.

    Permite variar reps/tiempo/carga serie a serie: carga por serie y
    esquema de reps como PARÁMETRO, sin necesidad de un modo dedicado.
    La carga puede expresarse en kg (weight), %1RM (percent_1rm) o RPE.
    """
    reps: Optional[int] = None
    work_time_in_seconds: Optional[int] = None
    weight: Optional[float] = None
    percent_1rm: Optional[float] = None
    rpe: Optional[float] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SetPrescriptionV2":
        def _f(key: str) -> Optional[float]:
            v = data.get(key)
            return float(v) if isinstance(v, (int, float)) else None

        return cls(
            reps=data.get("reps"),
            work_time_in_seconds=data.get("work_time_in_seconds"),
            weight=_f("weight"),
            percent_1rm=_f("percent_1rm"),
            rpe=_f("rpe"),
        )


# -------------------------------------------------------------------
# IntraSetV2 (estructura intra-serie)
# -------------------------------------------------------------------


@dataclass
class IntraSetV2:
    """Técnica intra-serie: cluster, rest-pause, myo-reps o drop set.

    mini_sets: reps de cada mini-esfuerzo (cluster/rest_pause/myo_reps).
    drops: lista de {weight, reps} para drop sets (sin descanso entre bajadas).
    rest_seconds: descanso corto entre mini-esfuerzos.
    """
    type: str
    rest_seconds: Optional[int] = None
    mini_sets: List[int] = field(default_factory=list)
    drops: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntraSetV2":
        t = str(data.get("type") or "").strip().lower()
        rest = data.get("rest_seconds")
        mini = [x for x in (data.get("mini_sets") or []) if isinstance(x, int)]
        drops = [d for d in (data.get("drops") or []) if isinstance(d, dict)]
        return cls(
            type=t,
            rest_seconds=rest if isinstance(rest, int) else None,
            mini_sets=mini,
            drops=drops,
        )


# -------------------------------------------------------------------
# ExerciseV2
# -------------------------------------------------------------------


@dataclass
class ExerciseV2:
    name: str

    reps: Optional[int] = None
    work_time_in_seconds: Optional[int] = None
    distance_in_meters: Optional[float] = None
    weight: Optional[float] = None
    percent_1rm: Optional[float] = None
    rpe: Optional[float] = None

    notes: Optional[str] = None
    help: Optional[str] = None

    sets: List[SetPrescriptionV2] = field(default_factory=list)
    intra_set: Optional["IntraSetV2"] = None
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

        distance_in_meters = data.get("distance_in_meters")
        if isinstance(distance_in_meters, (int, float)):
            distance_in_meters = float(distance_in_meters)
        else:
            distance_in_meters = None

        weight = data.get("weight")

        if isinstance(weight, (int, float)):
            weight = float(weight)
        else:
            weight = None

        def _f(key: str) -> Optional[float]:
            v = data.get(key)
            return float(v) if isinstance(v, (int, float)) else None

        percent_1rm = _f("percent_1rm")
        rpe = _f("rpe")

        sets_raw = data.get("sets") or []
        sets = [
            SetPrescriptionV2.from_dict(s)
            for s in sets_raw
            if isinstance(s, dict)
        ]

        intra_raw = data.get("intra_set")
        intra_set = IntraSetV2.from_dict(intra_raw) if isinstance(intra_raw, dict) else None

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
            "distance_in_meters",
            "weight",
            "percent_1rm",
            "rpe",
            "sets",
            "intra_set",
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
            distance_in_meters=distance_in_meters,
            weight=weight,
            percent_1rm=percent_1rm,
            rpe=rpe,
            notes=notes,
            help=help_text,
            sets=sets,
            intra_set=intra_set,
            extra=extra,
        )


# -------------------------------------------------------------------
# DeathBySpecV2 (variante de EMOM)
# -------------------------------------------------------------------


@dataclass
class DeathBySpecV2:
    """Variante Death-By de EMOM: las reps ascienden cada intervalo hasta el fallo.

    Las reps iniciales son el `reps` del ejercicio; `increment_by` es cuánto
    suben en cada intervalo (por defecto 1). No hay rounds fijos: acaba al fallar.
    """
    increment_by: int = 1

    @classmethod
    def from_dict(cls, data: Any) -> "DeathBySpecV2":
        if isinstance(data, dict):
            inc = data.get("increment_by")
            if isinstance(inc, int) and inc != 0:
                return cls(increment_by=inc)
        return cls()


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
    interval_in_seconds: Optional[int] = None

    rest_time_in_seconds: Optional[int] = None
    rest_between_exercises_in_seconds: Optional[int] = None
    rest_between_rounds_in_seconds: Optional[int] = None

    cadence: Optional[str] = None
    tempo: Optional[str] = None
    eccentric_neg: bool = False
    isometric_hold: bool = False
    death_by: Optional[DeathBySpecV2] = None

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
        mode = JobModeV2.from_raw(str(data.get("mode") or data.get("MODE")))

        desc_raw = data.get("description") or data.get("Description")
        description = desc_raw.strip() if isinstance(desc_raw, str) else None

        rounds = data.get("Rounds") if "Rounds" in data else data.get("rounds")
        if isinstance(rounds, int) and rounds <= 0:
            rounds = None  # schema no debería permitirlo, fallback defensivo

        work_time_in_seconds = data.get("work_time_in_seconds")
        work_time_in_minutes = data.get("work_time_in_minutes")
        interval_in_seconds = data.get("interval_in_seconds")

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

        tempo_raw = data.get("tempo") or data.get("Tempo")
        tempo = tempo_raw.strip() if isinstance(tempo_raw, str) else None

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

        db_raw = data.get("death_by")
        if isinstance(db_raw, dict):
            death_by = DeathBySpecV2.from_dict(db_raw)
        elif db_raw is True:
            death_by = DeathBySpecV2()
        else:
            death_by = None

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
            "mode",
            "description",
            "Description",
            "Rounds",
            "rounds",
            "work_time_in_seconds",
            "work_time_in_minutes",
            "interval_in_seconds",
            "rest_time_in_seconds",
            "Rest_between_exercises_in_seconds",
            "rest_between_exercises_in_seconds",
            "Rest_between_rounds_in_seconds",
            "rest_between_rounds_in_seconds",
            "cadence",
            "Cadence",
            "tempo",
            "Tempo",
            "Eccentric (NEG)",
            "eccentric_neg",
            "isometric (HOLD)",
            "Isometric (HOLD)",
            "isometric_hold",
            "death_by",
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
            interval_in_seconds=interval_in_seconds,
            rest_time_in_seconds=rest_time_in_seconds,
            rest_between_exercises_in_seconds=rest_between_exercises_in_seconds,
            rest_between_rounds_in_seconds=rest_between_rounds_in_seconds,
            cadence=cadence,
            tempo=tempo,
            eccentric_neg=eccentric_neg,
            isometric_hold=isometric_hold,
            death_by=death_by,
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