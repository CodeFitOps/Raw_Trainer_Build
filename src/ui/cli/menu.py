# src/ui/cli/menu.py
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from src.infrastructure.workout_registry import WorkoutRegistry, _project_root
from src.ui.cli.style import title, info, error, prompt

log = logging.getLogger(__name__)

RunFn = Callable[[Path], int]
ImportFn = Callable[[], int]
V2MenuFn = Callable[[], int]


def _select_workout_from_registry() -> Path | None:
    """
    Muestra los workouts importados (desde el registry) y deja elegir uno.
    Devuelve la ruta absoluta al fichero elegido o None si se cancela.
    """
    registry = WorkoutRegistry.load()
    records = registry.get_all()

    if not records:
        print(info("\nNo imported workouts found. Use option [2] to import one."))
        return None

    records = sorted(records, key=lambda r: (r.name or r.file_path).lower())

    print("\nAvailable imported workouts:")
    for idx, rec in enumerate(records, start=1):
        file_name = Path(rec.file_path).name
        label = rec.name or "(no name)"
        print(f"  {idx}) {label}  [{file_name}]")
    print("  0) Cancel")

    project_root = _project_root()

    while True:
        raw = input(prompt("\nChoose workout number (or '0' to cancel): ")).strip()

        if raw in {"0", "c", "C", "q", "Q"}:
            return None

        if not raw.isdigit():
            print(error("Invalid selection. Please enter a number."))
            continue

        idx = int(raw)
        if not (1 <= idx <= len(records)):
            print(error("Invalid selection. Out of range."))
            continue

        rec = records[idx - 1]
        path = project_root / rec.file_path

        if not path.is_file():
            print(
                error(
                    f"File for this workout does not exist: {path}. "
                    "Registry might be stale."
                )
            )
            continue

        return path


def menu_loop(run_fn: RunFn, import_fn: ImportFn, v2_menu_fn: V2MenuFn | None = None) -> int:
    """
    Bucle principal del menú interactivo (v1).

    - run_fn: función tipo _handle_preview(Path) -> int
    - import_fn: función tipo _handle_import_workout() -> int
    - v2_menu_fn: si se pasa, añade [4] V2 Menu.
    """
    while True:
        print(title("\n===================================="))
        print(title("  RawTrainer CLI  (interactive mode)"))
        print(title("===================================="))
        print()
        print(title("[1] Run Workout"))
        print(title("[2] Import Workout"))
        if v2_menu_fn is not None:
            print(title("[4] V2 Menu"))
        print(title("[3] Exit"))

        choice = input(prompt("> ")).strip()

        if choice == "1":
            path = _select_workout_from_registry()
            if path is None:
                continue
            code = run_fn(path)
            log.debug("Run workout finished with exit code %d", code)

        elif choice == "2":
            code = import_fn()
            log.debug("Import workout finished with exit code %d", code)

        elif choice == "4" and v2_menu_fn is not None:
            code = v2_menu_fn()
            log.debug("V2 menu finished with exit code %d", code)

        elif choice == "3":
            print(info("Bye!"))
            return 0

        else:
            valid = {"1", "2", "3"} | ({"4"} if v2_menu_fn is not None else set())
            print(error(f"Invalid option. Choose one of: {', '.join(sorted(valid))}"))