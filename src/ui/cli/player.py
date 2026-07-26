# src/ui/cli/player.py
"""Player DRIVEN: reproduce en la terminal una secuencia de segmentos.

Genérico: no sabe de modos, solo de segmentos (prepare/work/rest). Un executor
(src/application/driven) traduce cada job a segmentos y este player los
cronometra. Los modos sin executor caen al modo descriptivo (ficha + ENTER).
"""
from __future__ import annotations

import select
import sys
import time
from typing import List, Optional

from colorama import Fore, Style

from src.application.driven.executors import build_segments
from src.application.driven.segments import Segment
from src.domain_v2.workout_v2 import JobModeV2
from src.infrastructure import run_log
from src.ui.cli.preview_v2 import format_job_card
from src.ui.cli.style import success, title, info, job_title, prompt


def _mmss(seconds: int) -> str:
    m, s = divmod(max(0, int(seconds)), 60)
    return f"{m:02d}:{s:02d}"


def _kind_style(kind: str):
    """(etiqueta, color colorama) según el tipo de segmento."""
    if kind == "work":
        return "TRABAJO", Fore.GREEN + Style.BRIGHT
    if kind == "rest":
        return "DESCANSO", Fore.CYAN + Style.BRIGHT
    if kind == "window":
        return "AMRAP", Fore.MAGENTA + Style.BRIGHT
    if kind == "stopwatch":
        return "FOR TIME", Fore.GREEN + Style.BRIGHT
    return "PREPÁRATE", Fore.YELLOW + Style.BRIGHT


def _beep() -> None:
    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        pass


def _run_stopwatch(color: str) -> Optional[int]:
    """Cronómetro ascendente hasta que el usuario pulsa ENTER (for_time).

    Devuelve los segundos transcurridos (None si no hay terminal interactivo).
    """
    if not (sys.stdout.isatty() and sys.stdin.isatty()):
        print(info("   (cronómetro ascendente — requiere terminal interactivo; omitido)"))
        return None
    print(info("   ENTER cuando termines…"))
    start = time.monotonic()
    while True:
        elapsed = int(time.monotonic() - start)
        sys.stdout.write("\r   " + color + _mmss(elapsed) + Style.RESET_ALL + " " * 8)
        sys.stdout.flush()
        ready, _, _ = select.select([sys.stdin], [], [], 1.0)
        if ready:
            sys.stdin.readline()
            break
    total = int(time.monotonic() - start)
    sys.stdout.write("\r" + " " * 40 + "\r")
    sys.stdout.flush()
    print(success(f"   ⏱  Tiempo: {_mmss(total)}"))
    return total


def _run_segment(seg: Segment, nxt: Optional[Segment]) -> Optional[int]:
    label, color = _kind_style(seg.kind)
    head = f"{color}{label}{Style.RESET_ALL}"
    if seg.label and seg.kind != "rest":
        head += "  " + success(seg.label)
    if seg.kind == "work" and seg.total_rounds:
        head += info(f"   (ronda {seg.round_index}/{seg.total_rounds})")
    if seg.kind == "rest" and nxt is not None and nxt.kind in ("work", "window"):
        head += info(f"   luego: {nxt.label}")
    print(head)
    if seg.items:
        for it in seg.items:
            print(info(f"      · {it}"))

    _beep()

    if seg.kind == "stopwatch":
        return _run_stopwatch(color)

    remaining = seg.duration_seconds
    if not sys.stdout.isatty():
        # Sin terminal interactivo: no hacemos spam de cuenta atrás.
        print(f"   {_mmss(remaining)}")
        time.sleep(remaining)
        return None

    while remaining > 0:
        sys.stdout.write("\r   " + color + _mmss(remaining) + Style.RESET_ALL + " " * 8)
        sys.stdout.flush()
        time.sleep(1)
        remaining -= 1
    sys.stdout.write("\r" + " " * 40 + "\r")
    sys.stdout.flush()
    return None


def run_segments(segments: List[Segment], *, header: str = "") -> Optional[int]:
    """Reproduce los segmentos. Devuelve el tiempo del cronómetro (for_time) si lo hubo."""
    if not segments:
        print(info("   (nada que cronometrar en este job)\n"))
        return None
    total = sum(s.duration_seconds for s in segments)
    if header:
        print(job_title(header))
    print(info(f"   {len(segments)} segmentos · {_mmss(total)} en total  ·  (Ctrl-C para parar)\n"))
    auto_time: Optional[int] = None
    for i, seg in enumerate(segments):
        nxt = segments[i + 1] if i + 1 < len(segments) else None
        result = _run_segment(seg, nxt)
        if result is not None:
            auto_time = result
    print(success("   ✅ Bloque completado.\n"))
    return auto_time


def _ask(text: str) -> str:
    try:
        return input(prompt(text)).strip()
    except EOFError:
        return ""


def _ask_int(text: str) -> Optional[int]:
    raw = _ask(text)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _capture_job_result(job, auto_time: Optional[int]) -> dict:
    """Captura el resultado/score de un job según su modo, para el log.

    for_time: tiempo del cronómetro (automático). amrap: rondas + reps.
    Todos: nota opcional. (EDT/Death-By se añadirán con su executor driven.)
    """
    extra: dict = {}
    if job.mode is JobModeV2.FOR_TIME and auto_time is not None:
        extra["result_time_seconds"] = auto_time
    elif job.mode is JobModeV2.AMRAP:
        rounds = _ask_int("   Rondas completas (ENTER salta): ")
        reps = _ask_int("   Reps extra (ENTER salta): ")
        if rounds is not None:
            extra["result_rounds"] = rounds
        if reps is not None:
            extra["result_reps"] = reps
    note = _ask("   Nota (ENTER salta): ")
    if note:
        extra["note"] = note
    return extra


def drive_workout_v2(workout, *, source_path=None) -> None:
    """Reproduce el workout en modo driven, job a job, y guarda la sesión.

    interval/tabata/amrap/for_time/emom se cronometran; el resto cae al modo
    descriptivo. La sesión se registra en .run_logs_v2 (lo lee `stats`).
    """
    print(title(f"▶  {workout.name}  (modo driven)\n"))
    record = run_log.build_run_record_base(workout, source_path, mode="driven")
    start_ts = time.time()
    try:
        for s_idx, stage in enumerate(workout.stages, start=1):
            print(title(f"═══  Stage {s_idx}/{len(workout.stages)}: {stage.name}  ═══\n"))
            stage_rec = {
                "index": s_idx,
                "name": stage.name,
                "description": stage.description,
                "jobs": [],
            }
            for j_idx, job in enumerate(stage.jobs, start=1):
                segments = build_segments(job)
                header = (
                    f"── Job {j_idx}/{len(stage.jobs)} · {job.name} "
                    f"[{job.mode.mode_label()}] ──"
                )
                job_start = time.time()
                auto_time: Optional[int] = None
                if segments:
                    auto_time = run_segments(segments, header=header)
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
                job_rec = {
                    "index": j_idx,
                    "name": job.name,
                    "mode": job.mode.value,
                    "duration_seconds": int(time.time() - job_start),
                }
                job_rec.update(_capture_job_result(job, auto_time))
                stage_rec["jobs"].append(job_rec)
            record["stages"].append(stage_rec)
        print(success("🎉  Workout completado."))
    except KeyboardInterrupt:
        print(info("\n\n⏹  Sesión detenida (se guarda igualmente). ¡Buen trabajo!"))

    record["ended_at"] = run_log.now_iso()
    record["duration_seconds"] = int(time.time() - start_ts)
    try:
        target = run_log.save_run_record(record)
        print(info(f"\nSesión guardada en {target.name}"))
    except Exception as exc:  # noqa: BLE001
        print(info(f"\n(no se pudo guardar la sesión: {exc})"))
