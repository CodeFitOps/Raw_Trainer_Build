# src/ui/cli/menu.py
from __future__ import annotations

from pathlib import Path
from typing import Callable
import logging

from src.ui.cli.style import title, info, error, prompt
from src.infrastructure.workout_registry import WorkoutRegistry, _project_root

log = logging.getLogger(__name__)

RunFn = Callable[[Path], int]
ImportFn = Callable[[], int]


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

    # Ordenar por nombre si existe, si no por file_path
    records = sorted(records, key=lambda r: (r.name or r.file_path).lower())

    print("\nAvailable imported workouts:")
    for idx, rec in enumerate(records, start=1):
        file_name = Path(rec.file_path).name
        label = rec.name or "(no name)"
        print(f"  {idx}) {label}  [{file_name}]")
    print("  0) Cancel")

    project_root = _project_root()

    while True:
        raw = input(
            prompt("\nChoose workout number (or '0' to cancel): ")
        ).strip()

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
            # De momento solo dejamos volver a elegir
            continue

        return path


def menu_loop(run_fn: RunFn, import_fn: ImportFn) -> int:
    """
    Bucle principal del menú interactivo.

    - run_fn: función tipo _handle_preview(Path) -> int
             (carga, pretty-print y pregunta si correr el workout)
    - import_fn: función tipo _handle_import_workout() -> int
    """
    while True:
        print(title("\n===================================="))
        print(title("  RawTrainer CLI  (interactive mode)"))
        print(title("===================================="))
        print()
        print(title("[1] Run Workout"))
        print(title("[2] Import Workout"))
        print(title("[3] Exit"))

        choice = input(prompt("> ")).strip()

        if choice == "1":
            path = _select_workout_from_registry()
            if path is None:
                continue
            code = run_fn(path)
            log.debug("Run workout finished with exit code %d", code)
            # run_fn ya es interactiva; no añadimos pausa extra aquí.

        elif choice == "2":
            code = import_fn()
            log.debug("Import workout finished with exit code %d", code)
            # import_fn ya hace sus propias preguntas / prints.

        elif choice == "3":
            print(info("Bye!"))
            return 0

        else:
            print(error("Invalid option. Please choose 1, 2 or 3."))