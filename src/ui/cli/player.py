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

from colorama import Back, Fore, Style

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
from src.i18n import t
from src.ui.cli.preview_v2 import format_job_card
from src.ui.cli.style import (
    success, title, info, job_title, job_label, stage_title, stage_label, prompt,
)


def _mmss(seconds: int) -> str:
    m, s = divmod(max(0, int(seconds)), 60)
    return f"{m:02d}:{s:02d}"


def _dim(text: str) -> str:
    """Texto atenuado (pistas, metadatos secundarios)."""
    return f"{Style.DIM}{Fore.WHITE}{text}{Style.RESET_ALL}"


def _hl(text: str) -> str:
    """Texto resaltado (nombre de ejercicio, llamada a la acción)."""
    return f"{Style.BRIGHT}{Fore.WHITE}{text}{Style.RESET_ALL}"


# tipo de segmento -> (fondo del chip, texto del chip, color del reloj).
# La ETIQUETA del chip sale de i18n: chip.<kind>.
_KIND = {
    "work":      (Back.GREEN,   Fore.BLACK, Fore.GREEN),
    "rest":      (Back.CYAN,    Fore.BLACK, Fore.CYAN),
    "window":    (Back.MAGENTA, Fore.WHITE, Fore.MAGENTA),
    "density":   (Back.MAGENTA, Fore.WHITE, Fore.MAGENTA),
    "stopwatch": (Back.GREEN,   Fore.BLACK, Fore.GREEN),
    "set":       (Back.BLUE,    Fore.WHITE, Fore.CYAN),
    "prepare":   (Back.YELLOW,  Fore.BLACK, Fore.YELLOW),
}


def _chip_label(kind: str) -> str:
    return t(f"chip.{kind}") if kind in _KIND else "·"


def _chip(kind: str) -> str:
    """Etiqueta de tipo de segmento como 'chip' de color (fondo)."""
    bg, fg, _ = _KIND.get(kind, (Back.WHITE, Fore.BLACK, Fore.WHITE))
    return f"{bg}{fg}{Style.BRIGHT} {_chip_label(kind)} {Style.RESET_ALL}"


def _clock_color(kind: str) -> str:
    """Color (brillante) del reloj para un tipo de segmento."""
    return _KIND.get(kind, (None, None, Fore.WHITE))[2] + Style.BRIGHT


# Ritmo de "respiración" (medio ciclo, en segundos): rápido en esfuerzo y el
# doble de lento en descanso. El chip/reloj late brillante ↔ atenuado.
_BEAT = {
    "work": 0.7,
    "set": 0.7,
    "stopwatch": 0.7,
    "prepare": 0.7,
    "window": 1.0,
    "density": 1.0,
    "rest": 1.4,
}


def _breath_style(elapsed: float, half_period: float) -> str:
    """Estilo (DIM/NORMAL/BRIGHT) según la fase de respiración -> pulso suave."""
    cycle = 2.0 * max(0.1, half_period)
    s = math.sin((elapsed % cycle) / cycle * 2.0 * math.pi)
    if s < -0.33:
        return Style.DIM
    if s > 0.33:
        return Style.BRIGHT
    return Style.NORMAL


def _pulse_chip(kind: str, elapsed: float) -> str:
    """Chip del segmento 'respirando' al ritmo propio del tipo."""
    bg, fg, _ = _KIND.get(kind, (Back.WHITE, Fore.BLACK, Fore.WHITE))
    st = _breath_style(elapsed, _BEAT.get(kind, 0.9))
    return f"{bg}{fg}{st} {_chip_label(kind)} {Style.RESET_ALL}"


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


def _countdown_keys(seconds: int, kind: str) -> None:
    """Cuenta atrás con el chip y el reloj 'respirando' al ritmo del tipo.
    Beep en los últimos 3s. Teclas: espacio=pausa · s=saltar · q=salir."""
    color = _clock_color(kind)
    half = _BEAT.get(kind, 0.9)
    start = time.monotonic()
    end = start + seconds
    beeped = set()
    hint = _dim(t("player.keys_hint"))
    with _raw_mode():
        while True:
            now = time.monotonic()
            left = end - now
            if left <= 0:
                break
            r = int(left)
            if 0 < r <= 3 and r not in beeped:
                beeped.add(r)
                _beep()
            phase = now - start
            st = _breath_style(phase, half)
            chip = _pulse_chip(kind, phase)
            clock = color + st + _mmss(math.ceil(left)) + Style.RESET_ALL
            sys.stdout.write(f"\r      {chip}   ⏱  {clock}     {hint}    ")
            sys.stdout.flush()
            key = _poll_key(min(0.12, left))
            if key is None:
                continue
            if key == "q":
                raise _DrivenQuit()
            if key == "s":
                break
            if key in (" ", "p"):
                paused = time.monotonic()
                chip_p = f"{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT} {t('chip.paused')} {Style.RESET_ALL}"
                sys.stdout.write("\r      " + chip_p + _dim(t("player.paused_hint")) + " " * 20)
                sys.stdout.flush()
                while True:
                    k2 = _poll_key(0.2)
                    if k2 in (" ", "p"):
                        break
                    if k2 == "q":
                        raise _DrivenQuit()
                end += time.monotonic() - paused  # descontar la pausa
    sys.stdout.write("\r" + " " * 78 + "\r")
    sys.stdout.flush()
    return None


def _run_stopwatch(kind: str) -> Optional[int]:
    """Cronómetro ascendente hasta que el usuario pulsa ENTER (for_time).

    Devuelve los segundos transcurridos (None si no hay terminal interactivo).
    """
    if not (sys.stdout.isatty() and sys.stdin.isatty()):
        print(_dim(t("player.stopwatch_skipped")))
        return None
    color = _clock_color(kind)
    half = _BEAT.get(kind, 0.7)
    print(_dim(t("player.enter_when_done")))
    start = time.monotonic()
    while True:
        now = time.monotonic()
        elapsed = int(now - start)
        phase = now - start
        st = _breath_style(phase, half)
        chip = _pulse_chip(kind, phase)
        sys.stdout.write(f"\r      {chip}   ⏱  {color}{st}{_mmss(elapsed)}{Style.RESET_ALL}" + " " * 8)
        sys.stdout.flush()
        ready, _, _ = select.select([sys.stdin], [], [], 0.12)
        if ready:
            sys.stdin.readline()
            break
    total = int(time.monotonic() - start)
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()
    print(success(t("player.final_time", t=_mmss(total))))
    return total


def _run_set(kind: str) -> None:
    """Serie a tu ritmo: espera ENTER mientras el chip 'respira' (guía de ritmo)."""
    if not (sys.stdout.isatty() and sys.stdin.isatty() and _RAW_OK):
        _ask(t("player.enter_set_done"))
        return None
    hint = _dim(t("player.set_hint"))
    start = time.monotonic()
    with _raw_mode():
        while True:
            phase = time.monotonic() - start
            chip = _pulse_chip(kind, phase)
            sys.stdout.write(f"\r      {chip}   {hint}     ")
            sys.stdout.flush()
            key = _poll_key(0.12)
            if key is None:
                continue
            if key in ("\n", "\r"):
                break
            if key == "q":
                raise _DrivenQuit()
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()
    return None


def _run_segment(seg: Segment, nxt: Optional[Segment]) -> Optional[int]:
    # Línea de contexto (estática, sin chip): el chip late luego en la línea viva.
    ctx = ""
    if seg.kind == "rest":
        if nxt is not None and nxt.kind in ("work", "window", "set"):
            ctx = "   " + _dim(t("player.next_up")) + _hl(nxt.label or "")
    else:
        parts = ""
        if seg.label:
            parts += _hl(seg.label)
        if seg.total_rounds:
            parts += _dim(t("player.round", i=seg.round_index, total=seg.total_rounds))
        if parts:
            ctx = "   " + parts
    if ctx:
        print(ctx)
    if seg.items:
        for it in seg.items:
            print("        " + _dim("·") + " " + info(it))

    _beep()

    if seg.kind == "stopwatch":
        return _run_stopwatch(seg.kind)

    if seg.kind == "set":
        # Serie a tu ritmo: ENTER para avanzar (el chip respira mientras tanto).
        return _run_set(seg.kind)

    remaining = seg.duration_seconds
    if sys.stdout.isatty() and sys.stdin.isatty() and _RAW_OK:
        return _countdown_keys(remaining, seg.kind)

    # Sin terminal interactivo (o sin termios): estático, sin latido.
    print(f"      {_chip(seg.kind)}   ⏱  {_clock_color(seg.kind)}{_mmss(remaining)}{Style.RESET_ALL}")
    time.sleep(remaining)
    return None


def run_segments(segments: List[Segment], *, header: str = "") -> Optional[int]:
    """Reproduce los segmentos. Devuelve el tiempo del cronómetro (for_time) si lo hubo."""
    if not segments:
        print(_dim(t("player.nothing_to_time")))
        return None
    total = sum(s.duration_seconds for s in segments)
    if header:
        print(job_title(header))
    print(_dim(t("player.segments_summary", total=_mmss(total), n=len(segments))))
    print()
    auto_time: Optional[int] = None
    for i, seg in enumerate(segments):
        nxt = segments[i + 1] if i + 1 < len(segments) else None
        result = _run_segment(seg, nxt)
        if result is not None:
            auto_time = result
    print()
    print(success(t("player.block_done")))
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
    """Pausa hasta ENTER (llamada a la acción). Sin terminal interactivo, sigue."""
    _ask(t("player.start_prompt", msg=msg))


def _short(text, width: int = 90) -> str:
    """Descripción en una sola línea (espacios colapsados) y recortada para el índice."""
    s = " ".join(str(text).split())
    return s if len(s) <= width else s[: width - 1] + "…"


def _print_overview(workout) -> None:
    """Índice general de la sesión: nombre + descripción de workout, stages y
    jobs (SOLO nombre y descripción; la ficha completa se muestra job a job,
    justo antes de ejecutar cada uno)."""
    print(title(f"▶  {workout.name}   " + t("player.driven_suffix")))
    if workout.description:
        print(_dim(_short(workout.description, 120)))
    n_jobs = sum(len(st.jobs) for st in workout.stages)
    print(_dim(t("player.counts", stages=len(workout.stages), jobs=n_jobs)))
    print()
    print(stage_label(t("player.plan_index")))
    for s_idx, stage in enumerate(workout.stages, start=1):
        print()
        print("  " + stage_title(f"Stage {s_idx}: {stage.name}")
              + _dim("   " + t("player.n_jobs", n=len(stage.jobs))))
        if stage.description:
            print("      " + _dim(_short(stage.description)))
        for j_idx, job in enumerate(stage.jobs, start=1):
            print("      " + job_label(f"{j_idx}. {job.name}")
                  + _dim(f"   [{job.mode.mode_label()}]"))
            if job.description:
                print("         " + _dim(_short(job.description)))
    # Tiempo estimado de la sesión (mismo cálculo que preview/run).
    from src.application.estimate import (
        estimate_workout, fmt_duration, REST_BETWEEN_JOBS_DEFAULT,
    )
    est = estimate_workout(workout)
    print()
    print(title(t("est.total", total=fmt_duration(est["total"]))))
    print(_dim(t("est.breakdown",
                 work=fmt_duration(est["work"]), rest=fmt_duration(est["rest"]))))
    if est["assumed_rest"]:
        print(_dim(t("est.assumed", mins=REST_BETWEEN_JOBS_DEFAULT // 60)))
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
        print(success(t("player.pr_first", value=value, unit=unit)))
        return
    improved = value > best if higher_better else value < best
    if improved:
        print(success(t("player.pr_new", value=value, unit=unit, best=f"{best:g}")))
    else:
        print(_dim(t("player.pr_current", best=f"{best:g}", unit=unit, value=value)))


def _drive_death_by(job, prior_records, workout_name) -> dict:
    """Death-By: intervalos con reps ascendentes hasta el fallo. Devuelve el score."""
    interval = job.interval_in_seconds or job.work_time_in_seconds or 60
    ex = job.exercises[0] if job.exercises else None
    name = ex.name if ex else "Trabajo"
    start = ex.reps if (ex and ex.reps) else 1
    inc = job.death_by.increment_by if job.death_by else 1
    print(info(t("player.deathby_intro", start=start, inc=inc, interval=interval)))
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
        ans = _ask(t("player.deathby_ask", target=target)).lower()
        if ans in ("n", "no", "q", "f", "fallo"):
            break
        completed = k

    last_reps = start + (completed - 1) * inc if completed else 0
    print(success(t("player.deathby_result", rounds=completed, reps=last_reps)))
    _show_pr(prior_records, workout_name, job.name, "result_rounds", completed,
             higher_better=True, unit=t("unit.rounds"))
    return {"result_rounds": completed, "result_last_reps": last_reps}


def _capture_job_result(job, auto_time, prior_records, workout_name) -> dict:
    """Captura el resultado/score de un job según su modo, para el log (+ PR).

    for_time: tiempo del cronómetro (automático). amrap: rondas + reps.
    edt: reps por ejercicio -> densidad total. Todos: nota opcional.
    """
    extra: dict = {}
    print()
    print("   " + _hl(t("player.result")))
    if job.mode is JobModeV2.FOR_TIME and auto_time is not None:
        extra["result_time_seconds"] = auto_time
        _show_pr(prior_records, workout_name, job.name, "result_time_seconds",
                 auto_time, higher_better=False, unit=t("unit.seconds"))
    elif job.mode is JobModeV2.AMRAP:
        rounds = _ask_int(t("player.ask_rounds"))
        reps = _ask_int(t("player.ask_reps"))
        if rounds is not None:
            extra["result_rounds"] = rounds
        if reps is not None:
            extra["result_reps"] = reps
        if rounds is not None:
            _show_pr(prior_records, workout_name, job.name, "result_rounds",
                     rounds, higher_better=True, unit=t("unit.rounds"))
    elif job.mode is JobModeV2.EDT:
        total = 0
        per: dict = {}
        for ex in (job.exercises or []):
            r = _ask_int(t("player.ask_reps_of", name=ex.name))
            if r:
                per[ex.name] = r
                total += r
        extra["result_total_reps"] = total
        if per:
            extra["result_reps_by_exercise"] = per
        print(success(t("player.total_density", total=total)))
        _show_pr(prior_records, workout_name, job.name, "result_total_reps",
                 total, higher_better=True, unit=t("unit.reps"))
    note = _ask(t("common.ask_note"))
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
            _pause(f"Stage {s_idx}/{len(workout.stages)} · {stage.name}")
            print(stage_title(f"═══  Stage {s_idx}/{len(workout.stages)}: {stage.name}  ═══"))
            if stage.description:
                print(stage_label(_short(stage.description, 120)))
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
                # …y pausa para empezar cuando el usuario esté listo.
                _pause(f"Job {j_idx}/{len(stage.jobs)} · {job.name}")
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
                        print(info(t("player.no_timer", mode=job.mode.mode_label())))
                        _ask(t("player.enter_when_done"))
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
        print(success(t("player.workout_done")))
    except (KeyboardInterrupt, _DrivenQuit):
        print(info(t("player.session_stopped")))

    record["ended_at"] = run_log.now_iso()
    record["duration_seconds"] = int(time.time() - start_ts)
    try:
        target = run_log.save_run_record(record)
        print(info("\n" + t("common.saved_session", name=target.name)))
    except Exception as exc:  # noqa: BLE001
        print(info(t("player.save_failed", exc=exc)))
