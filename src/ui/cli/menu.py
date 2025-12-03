# src/ui/cli/menu.py
from __future__ import annotations

from pathlib import Path
from typing import Callable
import logging

from src.ui.cli.style import title, info, error, prompt

log = logging.getLogger(__name__)

ValidateFn = Callable[[Path], int]
PreviewAndRunFn = Callable[[Path], int]

DEFAULT_WORKOUT_DIR = Path("data/workouts_files")

def _list_yaml_files() -> list[Path]:
    """
    Busca automáticamente archivos .yaml y .yml en el directorio por defecto.
    """
    if not DEFAULT_WORKOUT_DIR.exists():
        return []

    files = [
        p for p in DEFAULT_WORKOUT_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in {".yaml", ".yml"}
    ]
    return sorted(files)

def _prompt_workout_path() -> Path | None:
    """
    Pide al usuario la ruta de un workout YAML.
    Ofrece autolistado desde DEFAULT_WORKOUT_DIR.
    """
    yaml_files = _list_yaml_files()

    if yaml_files:
        print("\nAvailable workout files:")
        for idx, f in enumerate(yaml_files, start=1):
            print(f"  {idx}) {f.name}")
        print("  0) Enter custom path")
    else:
        print("\n(No automatic workout files found.)")
        print("Please enter a path manually.")

    while True:
        raw = input(
            prompt("\nChoose file number or enter path (or 'c' to cancel): ")
        ).strip()

        # cancel
        if raw.lower() in {"c", "cancel", "q", "quit"}:
            return None

        # numeric selection
        if raw.isdigit() and yaml_files:
            idx = int(raw)
            if idx == 0:
                # user wants to enter custom path
                pass  # continue to manual mode
            elif 1 <= idx <= len(yaml_files):
                return yaml_files[idx - 1]
            else:
                print(error("Invalid selection."))
                continue

        # manual path mode
        p = Path(raw)
        if p.exists():
            return p

        print(error(f"Path '{raw}' does not exist. Try again."))

def menu_loop(
    validate_fn: ValidateFn,
    preview_and_run_fn: PreviewAndRunFn,
) -> int:
    """
    Bucle principal del menú interactivo.

    - validate_fn: función tipo _handle_validate(Path) -> int
    - preview_and_run_fn: función tipo _handle_preview_interactive(Path) -> int
    """
    while True:
        print(title("\n===================================="))
        print(title("  RawTrainer CLI  (interactive mode)"))
        print(title("===================================="))
        print(title("1)"), title("Validate workout file"))
        print(title("2)"), title("Preview workout file (validate + summary + optional manual run)"))
        print(title("3)"), title("Exit"))

        choice = input(prompt("> ")).strip()

        if choice == "1":
            path = _prompt_workout_path()
            if path is None:
                continue
            code = validate_fn(path)
            log.debug("Validate finished with exit code %d", code)
            input(prompt("\nPress Enter to return to the menu..."))

        elif choice == "2":
            path = _prompt_workout_path()
            if path is None:
                continue
            code = preview_and_run_fn(path)
            log.debug("Preview+run finished with exit code %d", code)
            # No pausa extra: la propia función es interactiva

        elif choice == "3":
            print(info("Bye!"))
            return 0

        else:
            print(error("Invalid option. Please choose 1, 2 or 3."))