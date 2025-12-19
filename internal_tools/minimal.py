#!/usr/bin/env python3
from __future__ import annotations

import shutil
import pyfiglet
from termcolor import cprint


def _center(s: str, cols: int) -> str:
    if len(s) >= cols:
        return s[:cols]
    return " " * ((cols - len(s)) // 2) + s


def _pad_to_width(s: str, width: int) -> str:
    if len(s) >= width:
        return s[:width]
    return s + (" " * (width - len(s)))


def _make_double_box(lines: list[str], box_w: int, *, pad_x: int = 3, pad_y: int = 1) -> list[str]:
    """
    Caja "más gruesa" con doble borde:
    - borde exterior: ╔═╗
    - borde interior: ┌─┐
    """
    inner_w = box_w - 4  # deja espacio para el doble borde (2 chars por lado)

    # Ajusta contenido al ancho interior (restando padding)
    content_w = max(1, inner_w - pad_x * 2)
    norm = [_pad_to_width(l, content_w) for l in lines]

    # Construye caja interior
    itop = "┌" + ("─" * (inner_w - 2)) + "┐"
    ibot = "└" + ("─" * (inner_w - 2)) + "┘"
    iempty = "│" + (" " * (inner_w - 2)) + "│"

    inner = [itop]
    for _ in range(pad_y):
        inner.append(iempty)
    for l in norm:
        inner.append("│" + (" " * pad_x) + l + (" " * pad_x) + "│")
    for _ in range(pad_y):
        inner.append(iempty)
    inner.append(ibot)

    # Envuelve con borde exterior
    top = "╔" + ("═" * (box_w - 2)) + "╗"
    bot = "╚" + ("═" * (box_w - 2)) + "╝"
    out = [top]
    for row in inner:
        out.append("║" + row + "║")
    out.append(bot)

    return out


def print_init_message() -> None:
    cols, lines = shutil.get_terminal_size((118, 48))

    # Banner principal (para medir ancho objetivo)
    title = pyfiglet.figlet_format(">_ codeEngTools ®", font="slant").rstrip("\n").splitlines()
    banner_w = min(max(len(l) for l in title), cols - 2)

    # --- Contenido del "monitor" ---
    prompt = pyfiglet.figlet_format(">_", font="big").rstrip("\n").splitlines()

    # Engranaje grande en ASCII "dots/blocks" (más legible que [*])
    gear = [
        "  ****  ",
        " oO   ** ",
        "o   .   o",
        "o  ( )  o",
        "o   '   o",
        " oO   Oo ",
        "  'ooo'  ",
    ]

    # Combina: prompt a la izquierda, gear a la derecha
    left_w = max(len(x) for x in prompt)
    right_w = max(len(x) for x in gear)
    ph = max(len(prompt), len(gear))

    prompt = [x.ljust(left_w) for x in prompt] + [" " * left_w] * (ph - len(prompt))
    gear = [x.ljust(right_w) for x in gear] + [" " * right_w] * (ph - len(gear))

    gap = "   "
    content = [prompt[i] + gap + gear[i] for i in range(ph)]

    # Caja del ancho del banner (como pediste)
    box_w = max(30, min(banner_w, cols - 2))

    # Si el contenido es más ancho que la caja, recorta un poco
    usable = box_w - 8  # aprox margen doble borde + padding
    content = [c[:usable] for c in content]

    box_lines = _make_double_box(content, box_w, pad_x=3, pad_y=1)

    # --- Render ---
    print()
    for ln in box_lines:
        cprint(_center(ln, cols), "magenta", attrs=["bold"])
    print()

    for ln in title:
        cprint(_center(ln[:banner_w], cols), "magenta", attrs=["bold"])

    cprint("FROM CODE TO CONTROL".center(cols), "white", attrs=["bold"])
    print()


if __name__ == "__main__":
    print_init_message()