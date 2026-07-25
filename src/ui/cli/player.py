# src/ui/cli/player.py
"""Player DRIVEN: reproduce en la terminal una secuencia de segmentos.

Genérico: no sabe de modos, solo de segmentos (prepare/work/rest). Un executor
(src/application/driven) traduce cada job a segmentos y este player los
cronometra. Los modos sin executor caen al modo descriptivo (ficha + ENTER).
"""
from __future__ import annotations

import sys
import time
from typing import List, Optional

from colorama import Fore, Style

from src.application.driven.executors import build_segments
from src.application.driven.segments import Segment
from src.ui.cli.preview_v2 import format_job_card
from src.ui.cli.style import success, title, info, job_title


def _mmss(seconds: int) -> str:
    m, s = divmod(max(0, int(seconds)), 60)
    return f"{m:02d}:{s:02d}"


def _kind_style(kind: str):
    """(etiqueta, color colorama) según el tipo de segmento."""
    if kind == "work":
        return "TRABAJO", Fore.GREEN + Style.BRIGHT
    if kind == "rest":
        return "DESCANSO", Fore.CYAN + Style.BRIGHT
    return "PREPÁRATE", Fore.YELLOW + Style.BRIGHT


def _beep() -> None:
    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        pass


def _run_segment(seg: Segment, nxt: Optional[Segment]) -> None:
    label, color = _kind_style(seg.kind)
    head = f"{color}{label}{Style.RESET_ALL}"
    if seg.kind == "work":
        head += "  " + success(seg.label)
        if seg.total_rounds:
            head += info(f"   (ronda {seg.round_index}/{seg.total_rounds})")
    elif seg.kind == "rest" and nxt is not None and nxt.kind == "work":
        head += info(f"   luego: {nxt.label}")
    print(head)

    _beep()
    remaining = seg.duration_seconds

    if not sys.stdout.isatty():
        # Sin terminal interactivo: no hacemos spam de cuenta atrás.
        print(f"   {_mmss(remaining)}")
        time.sleep(remaining)
        return

    while remaining > 0:
        sys.stdout.write("\r   " + color + _mmss(remaining) + Style.RESET_ALL + " " * 8)
        sys.stdout.flush()
        time.sleep(1)
        remaining -= 1
    sys.stdout.write("\r" + " " * 40 + "\r")
    sys.stdout.flush()


def run_segments(segments: List[Segment], *, header: str = "") -> None:
    if not segments:
        print(info("   (nada que cronometrar en este job)\n"))
        return
    total = sum(s.duration_seconds for s in segments)
    if header:
        print(job_title(header))
    print(info(f"   {len(segments)} segmentos · {_mmss(total)} en total  ·  (Ctrl-C para parar)\n"))
    for i, seg in enumerate(segments):
        nxt = segments[i + 1] if i + 1 < len(segments) else None
        _run_segment(seg, nxt)
    print(success("   ✅ Bloque completado.\n"))


def drive_workout_v2(workout) -> None:
    """Reproduce el workout en modo driven, job a job.

    interval/tabata se cronometran; el resto de modos caen al descriptivo.
    """
    print(title(f"▶  {workout.name}  (modo driven)\n"))
    try:
        for s_idx, stage in enumerate(workout.stages, start=1):
            print(title(f"═══  Stage {s_idx}/{len(workout.stages)}: {stage.name}  ═══\n"))
            for j_idx, job in enumerate(stage.jobs, start=1):
                segments = build_segments(job)
                header = (
                    f"── Job {j_idx}/{len(stage.jobs)} · {job.name} "
                    f"[{job.mode.mode_label()}] ──"
                )
                if segments:
                    run_segments(segments, header=header)
                else:
                    for line in format_job_card(job, j_idx, len(stage.jobs)):
                        print(line)
                    print()
                    print(info(
                        f"   (modo {job.mode.mode_label()} aún sin cronómetro "
                        f"— se muestra en modo descriptivo)"
                    ))
                    try:
                        input(info("   ENTER para continuar…"))
                    except EOFError:
                        pass
                    print()
        print(success("🎉  Workout completado."))
    except KeyboardInterrupt:
        print(info("\n\n⏹  Sesión detenida. ¡Buen trabajo!"))
