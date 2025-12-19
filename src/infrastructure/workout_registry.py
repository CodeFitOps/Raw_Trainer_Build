# src/infrastructure/workout_registry.py
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

log = logging.getLogger(__name__)

REGISTRY_FILENAME = "workouts_registry.json"


def _project_root() -> Path:
    """
    Devuelve la raíz del proyecto (donde vive el .git, main.py, etc.).
    Asume que este archivo está en src/infrastructure/.
    """
    return Path(__file__).resolve().parents[2]


def _registry_path() -> Path:
    return _project_root() / "data" / REGISTRY_FILENAME


@dataclass
class WorkoutRecord:
    """
    Registro simple de un workout importado/validado.
    file_path: ruta relativa al root del proyecto (ej: data/workouts_files/xxx.yaml)
    """
    file_path: str
    name: str | None = None
    description: str | None = None
    imported_at: str | None = None
    last_validated_at: str | None = None
    checksum: str | None = None


class WorkoutRegistry:
    """
    Pequeño wrapper para cargar/guardar el registro de workouts
    en un JSON: data/workouts_registry.json
    """

    def __init__(self, records: dict[str, WorkoutRecord] | None = None) -> None:
        self._records: dict[str, WorkoutRecord] = records or {}

    @classmethod
    def load(cls) -> WorkoutRegistry:
        """
        Carga el registro desde disco. Si no existe o está roto, devuelve
        un registro vacío.
        """
        path = _registry_path()
        if not path.exists():
            log.info("Workout registry not found at %s, starting empty.", path)
            return cls({})

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            log.error(
                "Failed to read workout registry %s: %s. Starting empty.",
                path,
                exc,
            )
            return cls({})

        if not isinstance(raw, dict):
            log.error("Workout registry %s has invalid format. Starting empty.", path)
            return cls({})

        workouts = raw.get("workouts", [])
        records: dict[str, WorkoutRecord] = {}

        if isinstance(workouts, list):
            for item in workouts:
                if not isinstance(item, dict):
                    continue
                fp = item.get("file_path")
                if not isinstance(fp, str):
                    continue
                records[fp] = WorkoutRecord(
                    file_path=fp,
                    name=item.get("name"),
                    description=item.get("description"),
                    imported_at=item.get("imported_at"),
                    last_validated_at=item.get("last_validated_at"),
                    checksum=item.get("checksum"),
                )

        log.debug(
            "Loaded workout registry from %s with %d records",
            path,
            len(records),
        )
        return cls(records)

    def save(self) -> None:
        """
        Guarda el registro actual en disco (JSON).
        """
        path = _registry_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        payload: dict[str, Any] = {
            "version": 1,
            "workouts": [asdict(r) for r in self._records.values()],
        }

        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        log.debug(
            "Workout registry saved to %s with %d records",
            path,
            len(self._records),
        )

    def register_import(
            self,
            file_path: Path,
            name: str | None,
            description: str | None,
            checksum: str | None = None,
    ) -> WorkoutRecord:
        """
        Registra (o actualiza) la entrada para un workout importado.

        file_path: ruta absoluta al fichero en el repo.
        """
        rel_path = file_path.relative_to(_project_root())
        key = rel_path.as_posix()
        now = datetime.now(timezone.utc).isoformat()

        # Si no nos pasan checksum, lo calculamos del fichero ya copiado al repo.
        # (Esto es la "integrity base" para detectar modificaciones posteriores.)
        checksum_final = checksum
        if checksum_final is None:
            checksum_final = compute_sha256(file_path)

        rec = self._records.get(key)
        if rec is None:
            rec = WorkoutRecord(
                file_path=key,
                name=name,
                description=description,
                imported_at=now,
                last_validated_at=now,
                checksum=checksum_final,
            )
        else:
            # Actualizamos info, mantenemos imported_at original
            rec.name = name
            rec.description = description
            rec.last_validated_at = now
            rec.checksum = checksum_final

        self._records[key] = rec
        log.info("Registered imported workout %s (%s)", name or "?", key)
        return rec
    def get_all(self) -> list[WorkoutRecord]:
        """
        Por si luego queremos listar todos los workouts importados
        desde UI/CLI.
        """
        return list(self._records.values())