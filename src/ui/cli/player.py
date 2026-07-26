# src/ui/cli/player.py
"""Player DRIVEN: reproduce en la terminal una secuencia de segmentos.

Genérico: no sabe de modos, solo de segmentos (prepare/work/rest). Un executor
(src/application/driven) traduce cada job a segmentos y este player los
cronometra. Los modos sin executor caen al modo descriptivo (ficha + ENTER).
"""
from __future__ import annotations

import contextlib
import math
import select
import sys
import time
from typing import List, Optional

from colorama import Fore, Style

try:
    import termios
    import tty
    _RAW_OK = True
except Exception:  # pragma: no cover - Windows u otros sin termios
    _RAW_OK = False

from src.application.driven.executors import build_segments, PREPARE_SECONDS
from src.application.driven.segments import Segment
from src.application.driven import scoring
from src.domain_v2.workout_v2 import JobModeV2
from src.infrastructure import run_log
from src.ui.cli.preview_v2 import format_job_card
from src.ui.cli.style import (
    success, title, info, job_title, job_label, stage_title, stage_label, prompt,
)


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
    if kind == "density":
        return "EDT", Fore.MAGENTA + Style.BRIGHT
    if kind == "stopwatch":
        return "FOR TIME", Fore.GREEN + Style.BRIGHT
    if kind == "set":
        return "SERIE", Fore.GREEN + Style.BRIGHT
    return "PREPÁRATE", Fore.YELLOW + Style.BRIGHT


def _beep() -> None:
    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        pass


class _DrivenQuit(Exception):
    """Señal de 'salir' desde el player (tecla q durante la cuenta atrás)."""


@contextlib.contextmanager
def _raw_mode():
    """Terminal en cbreak para leer teclas sueltas; restaura SIEMPRE al salir."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _poll_key(timeout: float):
    ready, _, _ = select.select([sys.stdin], [], [], max(0.0, timeout))
    if ready:
        return sys.stdin.read(1)
    return None


def _countdown_keys(seconds: int, color: str) -> None:
    """Cuenta atrás interactiva: espacio=pausa · s=saltar · q=salir. Beep últimos 3s."""
    end = time.monotonic() + seconds
    beeped = set()
    hint = info("   [espacio=pausa · s=saltar · q=salir]")
    with _raw_mode():
        while True:
            left = end - time.monotonic()
            if left <= 0:
                break
            r = int(left)
            if 0 < r <= 3 and r not in beeped:
                beeped.add(r)
                _beep()
            sys.stdout.write(
                "\r   " + color + _mmss(math.ceil(left)) + Style.RESET_ALL + hint + "   "
            )
            sys.stdout.flush()
            key = _poll_key(min(0.2, left))
            if key is None:
                continue
            if key == "q":
                raise _DrivenQuit()
            if key == "s":
                break
            if key in (" ", "p"):
                paused = time.monotonic()
                sys.stdout.write(
                    "\r   " + Fore.YELLOW + Style.BRIGHT + "PAUSA" + Style.RESET_ALL
                    + info("  (espacio=seguir · q=salir)") + "        "
                )
                sys.stdout.flush()
                while True:
                    k2 = _poll_key(0.2)
                    if k2 in (" ", "p"):
                        break
                    if k2 == "q":
                        raise _DrivenQuit()
                end += time.monotonic() - paused  # descontar la pausa
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()
    return None


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

    if seg.kind == "set":
        # Serie a tu ritmo: se avanza con ENTER (no hay cuenta atrás).
        _ask("   ENTER al terminar la serie… ")
        return None

    remaining = seg.duration_seconds
    if sys.stdout.isatty() and sys.stdin.isatty() and _RAW_OK:
        return _countdown_keys(remaining, color)

    # Sin terminal interactivo (o sin termios): cuenta atrás simple sin teclas.
    print(f"   {_mmss(remaining)}")
    time.sleep(remaining)
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


def _pause(msg: str) -> None:
    """Pausa hasta ENTER. Si no hay terminal interactivo, continúa sin bloquear."""
    _ask(f"⏸  {msg}  ·  (ENTER)  ")


def _short(text, width: int = 90) -> str:
    """Descripción en una sola línea (espacios colapsados) y recortada para el índice."""
    t = " ".join(str(text).split())
    return t if len(t) <= width else t[: width - 1] + "…"


def _print_overview(workout) -> None:
    """Índice general de la sesión: nombre + descripción de workout, stages y
    jobs (SOLO nombre y descripción; la ficha completa se muestra job a job,
    justo antes de ejecutar cada uno)."""
    print(title(f"▶  {workout.name}   (modo driven)"))
    if workout.description:
        print(info(_short(workout.description, 120)))
    n_jobs = sum(len(st.jobs) for st in workout.stages)
    print(info(f"{len(workout.stages)} stages · {n_jobs} jobs"))
    print()
    print(stage_label("Plan de la sesión (índice):"))
    for s_idx, stage in enumerate(workout.stages, start=1):
        print()
        print("  " + stage_title(f"Stage {s_idx}: {stage.name}")
              + info(f"   ({len(stage.jobs)} jobs)"))
        if stage.description:
            print("      " + info(_short(stage.description)))
        for j_idx, job in enumerate(stage.jobs, start=1):
            print("      " + job_label(f"{j_idx}. {job.name}")
                  + info(f"   [{job.mode.mode_label()}]"))
            if job.description:
                print("         " + info(_short(job.description)))
    print()


def _show_pr(prior_records, workout_name, job_name, score_key, value,
             *, higher_better: bool, unit: str) -> None:
    """Compara `value` con la mejor marca previa y lo anuncia (PR)."""
    if value is None:
        return
    best = scoring.best_previous(
        prior_records, workout_name, job_name, score_key, higher_better=higher_better
    )
    if best is None:
        print(success(f"   ⭐ Primera marca registrada: {value} {unit}"))
        return
    improved = value > best if higher_better else value < best
    if improved:
        print(success(f"   🏆 ¡NUEVO PR! {value} {unit}  (anterior: {best:g})"))
    else:
        print(info(f"   PR actual: {best:g} {unit}  (esta vez: {value})"))


def _drive_death_by(job, prior_records, workout_name) -> dict:
    """Death-By: intervalos con reps ascendentes hasta el fallo. Devuelve el score."""
    interval = job.interval_in_seconds or job.work_time_in_seconds or 60
    ex = job.exercises[0] if job.exercises else None
    name = ex.name if ex else "Trabajo"
    start = ex.reps if (ex and ex.reps) else 1
    inc = job.death_by.increment_by if job.death_by else 1
    print(info(
        f"   Death-By: empiezas en {start} reps, +{inc} por intervalo de "
        f"{interval}s, hasta el fallo.\n"
    ))
    _run_segment(Segment(kind="prepare", duration_seconds=PREPARE_SECONDS, label=""), None)

    completed = 0
    cap = 60  # cortafuegos: nadie sobrevive 60 rondas ascendentes
    for k in range(1, cap + 1):
        target = start + (k - 1) * inc
        seg = Segment(
            kind="work",
            duration_seconds=interval,
            label=f"{name} · {target} reps",
            round_index=k,
            total_rounds=0,
            items=[f"objetivo: {target} reps dentro del intervalo"],
        )
        _run_segment(seg, None)
        ans = _ask(f"   ¿Completaste {target} reps? (ENTER=sí / n=no): ").lower()
        if ans in ("n", "no", "q", "f", "fallo"):
            break
        completed = k

    last_reps = start + (completed - 1) * inc if completed else 0
    print(success(f"\n   💀 Death-By: {completed} rondas (hasta {last_reps} reps)."))
    _show_pr(prior_records, workout_name, job.name, "result_rounds", completed,
             higher_better=True, unit="rondas")
    return {"result_rounds": completed, "result_last_reps": last_reps}


def _capture_job_result(job, auto_time, prior_records, workout_name) -> dict:
    """Captura el resultado/score de un job según su modo, para el log (+ PR).

    for_time: tiempo del cronómetro (automático). amrap: rondas + reps.
    edt: reps por ejercicio -> densidad total. Todos: nota opcional.
    """
    extra: dict = {}
    if job.mode is JobModeV2.FOR_TIME and auto_time is not None:
        extra["result_time_seconds"] = auto_time
        _show_pr(prior_records, workout_name, job.name, "result_time_seconds",
                 auto_time, higher_better=False, unit="s")
    elif job.mode is JobModeV2.AMRAP:
        rounds = _ask_int("   Rondas completas (ENTER salta): ")
        reps = _ask_int("   Reps extra (ENTER salta): ")
        if rounds is not None:
            extra["result_rounds"] = rounds
        if reps is not None:
            extra["result_reps"] = reps
        if rounds is not None:
            _show_pr(prior_records, workout_name, job.name, "result_rounds",
                     rounds, higher_better=True, unit="rondas")
    elif job.mode is JobModeV2.EDT:
        total = 0
        per: dict = {}
        for ex in (job.exercises or []):
            r = _ask_int(f"   Reps de {ex.name} (ENTER 0): ")
            if r:
                per[ex.name] = r
                total += r
        extra["result_total_reps"] = total
        if per:
            extra["result_reps_by_exercise"] = per
        print(success(f"   Densidad total: {total} reps"))
        _show_pr(prior_records, workout_name, job.name, "result_total_reps",
                 total, higher_better=True, unit="reps")
    note = _ask("   Nota (ENTER salta): ")
    if note:
        extra["note"] = note
    return extra


def drive_workout_v2(workout, *, source_path=None) -> None:
    """Reproduce el workout en modo driven y guarda la sesión.

    Flujo: (1) índice general de la sesión, (2) pausa antes de cada stage,
    (3) ficha completa del job + pausa antes de ejecutarlo. Los modos con
    executor se cronometran; el resto se hace a ritmo del usuario. La sesión
    se registra en .run_logs_v2 (lo lee `stats`).
    """
    # 1) Índice general de toda la sesión (nombre + descripción, sin fichas).
    _print_overview(workout)
    record = run_log.build_run_record_base(workout, source_path, mode="driven")
    prior_records = run_log.load_all_records()  # sesiones anteriores, para PRs
    start_ts = time.time()
    try:
        for s_idx, stage in enumerate(workout.stages, start=1):
            # 2) Pausa antes de cada stage (transición / descanso entre bloques).
            print()
            _pause(f"Empezar Stage {s_idx}/{len(workout.stages)}: {stage.name}")
            print(stage_title(f"═══  Stage {s_idx}/{len(workout.stages)}: {stage.name}  ═══"))
            if stage.description:
                print(stage_label(_short(stage.description, 120)))
            print()
            stage_rec = {
                "index": s_idx,
                "name": stage.name,
                "description": stage.description,
                "jobs": [],
            }
            for j_idx, job in enumerate(stage.jobs, start=1):
                # 3) Ficha COMPLETA del job justo antes de ejecutarlo…
                print()
                for line in format_job_card(job, j_idx, len(stage.jobs)):
                    print(line)
                print()
                # …y pausa para empezar cuando el usuario esté listo.
                _pause(f"Empezar job {j_idx}/{len(stage.jobs)}: {job.name}")
                job_start = time.time()

                if job.mode is JobModeV2.EMOM and job.death_by is not None:
                    job_extra = _drive_death_by(job, prior_records, workout.name)
                else:
                    segments = build_segments(job)
                    auto_time: Optional[int] = None
                    if segments:
                        auto_time = run_segments(segments, header="")
                    else:
                        # Job sin cronómetro (vacío / a mano): se hace a tu ritmo.
                        print(info(
                            f"   (modo {job.mode.mode_label()} sin cronómetro "
                            f"— hazlo a tu ritmo)"
                        ))
                        _ask("   ENTER al terminar el job… ")
                        print()
                    job_extra = _capture_job_result(
                        job, auto_time, prior_records, workout.name
                    )

                job_rec = {
                    "index": j_idx,
                    "name": job.name,
                    "mode": job.mode.value,
                    "duration_seconds": int(time.time() - job_start),
                }
                job_rec.update(job_extra)
                stage_rec["jobs"].append(job_rec)
            record["stages"].append(stage_rec)
        print(success("🎉  Workout completado."))
    except (KeyboardInterrupt, _DrivenQuit):
        print(info("\n\n⏹  Sesión detenida (se guarda igualmente). ¡Buen trabajo!"))

    record["ended_at"] = run_log.now_iso()
    record["duration_seconds"] = int(time.time() - start_ts)
    try:
        target = run_log.save_run_record(record)
        print(info(f"\nSesión guardada en {target.name}"))
    except Exception as exc:  # noqa: BLE001
        print(info(f"\n(no se pudo guardar la sesión: {exc})"))
