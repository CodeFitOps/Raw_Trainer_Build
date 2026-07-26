# src/ui/cli/menu.py
"""Menú de terminal ENRIQUECIDO: el hub de RawTrainer.

Piel fina sobre la capa de aplicación (library, components) y los handlers de
main_cli — exactamente lo mismo que consumirá la futura GUI. Centrado en la
biblioteca: la ves siempre, eliges un workout por número y actúas sobre él sin
retipear (ver / ejecutar / driven / borrar). Sin dependencias externas.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from src.application import library
from src.ui.cli.style import title, info, error, success, prompt


# ---------------------------------------------------------------------------
# Entrada robusta (EOF/Ctrl-C -> None = cancelar/salir)
# ---------------------------------------------------------------------------

def _ask(text: str) -> Optional[str]:
    try:
        return input(prompt(text)).strip()
    except (EOFError, KeyboardInterrupt):
        return None


def _yes(text: str) -> bool:
    r = _ask(text)
    return r is not None and r.lower() in ("s", "si", "sí", "y", "yes")


def _pause() -> None:
    _ask("\n[ENTER para continuar]")


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def _print_main(files: List[Path]) -> None:
    print(title("\n══════════════ RawTrainer ══════════════"))
    if files:
        print(info(f"Biblioteca ({len(files)}) — elige un número para actuar:"))
        for i, f in enumerate(files, start=1):
            print(f"  {i:>2}) {library.peek_name(f)}")
    else:
        print(info("Biblioteca vacía — crea uno con 'n' o carga con 'f'."))
    print()
    print(info("Acciones:"))
    print("   n) Nuevo workout (asistente)      f) Cargar desde fichero")
    print("   c) Componentes (stages/jobs)      s) Estadísticas y marcas")
    print("   q) Salir")
    print(title("════════════════════════════════════════"))


# ---------------------------------------------------------------------------
# Submenú: acciones sobre un workout de la biblioteca
# ---------------------------------------------------------------------------

def _workout_actions(path: Path) -> None:
    from src.ui.cli import main_cli  # lazy: evita import circular
    while True:
        name = library.peek_name(path)
        print(title(f"\n── {name} ──"))
        print("  1) Ver resumen        2) Ver completo")
        print("  3) Ejecutar (descriptivo)   4) Modo driven (cronómetros)")
        print("  5) Eliminar           0) Volver")
        choice = _ask("Acción: ")
        if choice is None or choice in ("0", "b", ""):
            return
        if choice == "1":
            main_cli.cmd_preview(str(path), full=False)
        elif choice == "2":
            main_cli.cmd_preview(str(path), full=True)
        elif choice == "3":
            main_cli.cmd_run(str(path))
        elif choice == "4":
            main_cli.cmd_drive(str(path))
        elif choice == "5":
            if _yes(f"¿Eliminar '{name}'? [s/N]: "):
                main_cli.cmd_remove(str(path))
                return  # el fichero ya no existe
            continue
        else:
            print(error("Opción no válida."))
            continue
        _pause()


# ---------------------------------------------------------------------------
# Submenú: componentes
# ---------------------------------------------------------------------------

def _components_menu() -> None:
    from src.ui.cli import main_cli
    print(title("\n── Componentes reutilizables ──"))
    print("  1) Listar stages y jobs")
    print("  2) Reconstruir desde la biblioteca")
    print("  0) Volver")
    choice = _ask("Acción: ")
    if choice == "1":
        main_cli.cmd_components(rebuild=False)
    elif choice == "2":
        main_cli.cmd_components(rebuild=True)


# ---------------------------------------------------------------------------
# Bucle principal
# ---------------------------------------------------------------------------

def menu_loop() -> int:
    from src.ui.cli import main_cli
    while True:
        files = library.library_files()
        _print_main(files)
        choice = _ask("Elige (nº de workout o acción): ")

        if choice is None or choice.lower() in ("q", "0", "salir", "quit"):
            print(info("Hasta luego."))
            return 0

        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(files):
                _workout_actions(files[idx - 1])
            else:
                print(error("Número fuera de rango."))
                _pause()
            continue

        key = choice.lower()
        if key == "n":
            main_cli.cmd_new()
            _pause()
        elif key == "f":
            p = _ask("Ruta al fichero YAML (ENTER cancela): ")
            if p:
                main_cli.cmd_load(p)
                _pause()
        elif key == "c":
            _components_menu()
            _pause()
        elif key == "s":
            main_cli.cmd_stats()
            _pause()
        else:
            print(error("Opción no válida."))
            _pause()
