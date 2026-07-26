# src/ui/cli/menu.py
"""Menú de terminal: la misma operativa que la CLI, navegable con números.

Es una 'piel' fina sobre la capa de aplicación (library) y los handlers de
main_cli — exactamente lo mismo que consumirá la futura GUI.
"""
from __future__ import annotations

from src.application import library
from src.ui.cli.style import title, info, error


MENU = """
============ RawTrainer ============
  1) Run workout (de tu biblioteca)
  2) Run workout desde un fichero
  3) Cargar workout a tu biblioteca
  4) Ver biblioteca
  5) Estadísticas
  6) Modo DRIVEN — la app dirige (cronómetros)
  0) Salir
====================================
"""


def _print_library() -> list:
    files = library.library_files()
    if not files:
        print(info("Tu biblioteca está vacía. Usa la opción 3 para añadir uno."))
        return files
    print(title(f"\nTu biblioteca ({len(files)}):"))
    for idx, f in enumerate(files, start=1):
        print(f"  {idx:>2}) {f.name:<44} {info(library.peek_name(f))}")
    return files


def menu_loop() -> int:
    from src.ui.cli import main_cli  # lazy: evita import circular

    while True:
        print(MENU)
        try:
            choice = input("Elige una opción: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(info("\nHasta luego."))
            return 0

        if choice in ("0", "q", "quit", "salir"):
            print(info("Hasta luego."))
            return 0

        try:
            if choice == "1":
                files = _print_library()
                if files:
                    sel = input("\nNúmero o nombre (ENTER cancela): ").strip()
                    if sel:
                        main_cli.cmd_run(sel)
            elif choice == "2":
                p = input("Ruta al fichero YAML: ").strip()
                if p:
                    main_cli.cmd_run(p)
            elif choice == "3":
                p = input("Ruta al fichero YAML a cargar: ").strip()
                if p:
                    main_cli.cmd_load(p)
            elif choice == "4":
                main_cli.cmd_list()
            elif choice == "5":
                main_cli.cmd_stats()
            elif choice == "6":
                files = _print_library()
                if files:
                    sel = input("\nNúmero o nombre (ENTER cancela): ").strip()
                    if sel:
                        main_cli.cmd_drive(sel)
            else:
                print(error("Opción no válida."))
            input("\n[ENTER para continuar]")
        except (EOFError, KeyboardInterrupt):
            print("")
            return 0
