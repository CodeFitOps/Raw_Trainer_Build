# src/ui/cli/menu.py

from __future__ import annotations

from pathlib import Path
from typing import Callable
import logging

from src.ui.cli.style import title, info, error, prompt

log = logging.getLogger(__name__)

ValidateFn = Callable[[Path], int]
PreviewAndRunFn = Callable[[Path], int]
ImportFn = Callable[[], int]  # no path argument

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
        raw = input(prompt("\nChoose file number or enter path (or 'c' to cancel): ")).strip()

        # cancel
        if raw.lower() in {"c", "cancel", "q", "quit"}:
            return None

        # numeric selection
        if raw.isdigit() and yaml_files:
            idx = int(raw)
            if idx == 0:
                # user wants to enter custom path → fall through to manual mode
                pass
            elif 1 <= idx <= len(yaml_files):
                return yaml_files[idx - 1]
            else:
                print(error("Invalid selection."))
                continue

        # manual path mode
        p = Path(raw).expanduser()
        if p.exists() and p.is_file():
            return p

        print(error(f"Path '{raw}' does not exist or is not a file. Try again."))


def menu_loop(validate_fn, preview_and_run_fn, import_fn=None, mobile_mode=False):
    """
    Bucle principal del menú interactivo.

    - validate_fn: función tipo _handle_validate(Path) -> int
    - preview_and_run_fn: función tipo _handle_preview_interactive(Path) -> int
    - import_fn: función sin argumentos para importar workouts (opcional).
    """
    while True:
        print(title("\n===================================="))
        print(title("  RawTrainer CLI  (interactive mode)"))
        print(title("===================================="))
        if mobile_mode:
            print(info("[MOBILE MODE ENABLED]"))
            print(info("Use F1/F2/F3/F4 or tap shortcuts in your SSH app."))
        # Dejamos claro el mapping números / teclas rápidas (F1..F4)
        print(title("1) [F1] Import workout file"))
        print(title("2) [F2] Validate workout file"))
        print(title("3) [F3] Preview + optional run"))
        print(title("4) [F4] Exit"))

        choice = input(prompt("> ")).strip()

        if choice in ("1", "f1", "F1"):
            if import_fn is None:
                print(error("Import function not available."))
                continue
            code = import_fn()
            log.debug("Import finished with exit code %d", code)
            input(prompt("\nPress Enter to return to the menu..."))

        elif choice in ("2", "f2", "F2"):
            path = _prompt_workout_path()
            if path is None:
                continue
            code = validate_fn(path)
            log.debug("Validate finished with exit code %d", code)
            input(prompt("\nPress Enter to return to the menu..."))

        elif choice in ("3", "f3", "F3"):
            path = _prompt_workout_path()
            if path is None:
                continue
            code = preview_and_run_fn(path)
            log.debug("Preview+run finished with exit code %d", code)
            # La propia función ya es interactiva, no metemos pausa extra

        elif choice in ("4", "f4", "F4"):
            print(info("Bye!"))
            return 0

        else:
            print(error("Invalid option. Please choose 1, 2, 3 or 4."))