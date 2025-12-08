# src/infrastructure/run_history_v2.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

DEFAULT_HISTORY_FILE = Path.home() / ".rawtrainer_history" / "runs_v2.jsonl"


@dataclass
class RunHistoryLoggerV2:
    """
    Logger muy simple:
    - Escribe una línea JSON por ejecución de workout.
    - Por defecto en ~/.rawtrainer_history/runs_v2.jsonl
    """

    history_file: Path = DEFAULT_HISTORY_FILE

    def __post_init__(self) -> None:
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: Dict[str, Any]) -> None:
        """
        Añade un registro (ya serializable a JSON) como una línea JSON.
        """
        line = json.dumps(record, ensure_ascii=False)
        with self.history_file.open("a", encoding="utf-8") as f:
            f.write(line + "\n")