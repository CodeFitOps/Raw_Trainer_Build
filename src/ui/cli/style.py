# src/ui/cli/style.py
from __future__ import annotations

import logging
from colorama import init, Fore, Style

log = logging.getLogger(__name__)

# Inicializamos colorama para Windows y para que resetee solo
init(autoreset=True)


def success(text: str) -> str:
    """Texto para mensajes de éxito."""
    return f"{Style.BRIGHT}{Fore.GREEN}{text}{Style.RESET_ALL}"


def error(text: str) -> str:
    """Texto para mensajes de error."""
    return f"{Style.BRIGHT}{Fore.RED}{text}{Style.RESET_ALL}"


def title(text: str) -> str:
    """Título principal (workout, header global)."""
    return f"{Style.BRIGHT}{Fore.MAGENTA}{text}{Style.RESET_ALL}"


def stage_title(text: str) -> str:
    """Título de stage."""
    return f"{Style.BRIGHT}{Fore.MAGENTA}{text}{Style.RESET_ALL}"


def job_title(text: str) -> str:
    """Título de job."""
    return f"{Style.BRIGHT}{Fore.MAGENTA}{text}{Style.RESET_ALL}"


def workout_label(label: str) -> str:
    """Label de propiedad a nivel workout (mismo color que la cabecera)."""
    return f"{Style.BRIGHT}{Fore.MAGENTA}{label}{Style.RESET_ALL}"


def stage_label(label: str) -> str:
    """Label de propiedad a nivel stage (mismo color que la cabecera)."""
    return f"{Style.BRIGHT}{Fore.MAGENTA}{label}{Style.RESET_ALL}"


def job_label(label: str) -> str:
    """Label de propiedad a nivel job (mismo color que la cabecera)."""
    return f"{Fore.MAGENTA}{label}{Style.RESET_ALL}"


def exercise(text: str) -> str:
    """Línea de ejercicio (verde)."""
    return f"{text}{Style.RESET_ALL}"


def info(text: str) -> str:
    """Mensajes informativos / valores (gris/blanco)."""
    return f"{Fore.WHITE}{text}{Style.RESET_ALL}"


def prompt(text: str) -> str:
    """Prompts de entrada."""
    return f"{Style.BRIGHT}{Fore.YELLOW}{text}{Style.RESET_ALL}"