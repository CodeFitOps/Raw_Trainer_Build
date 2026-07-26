# src/ui/cli/main_cli.py
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional, Tuple

from src.application import library
from src.application.workout_loader import WorkoutLoadError
from src.infrastructure.logging_setup import configure_logging
from src.ui.cli.preview_v2 import format_workout_v2_summary, format_workout_v2_full
from src.ui.cli.run_v2 import run_workout_v2_interactive
from src.infrastructure.stats_v2 import build_stats_report, build_pr_report, RUN_LOGS_DIR
from src.ui.cli.style import success, error, title, info
from src.i18n import t

log = logging.getLogger(__name__)


# ======================================================================
# Helpers
# ======================================================================

def _resolve_and_load(arg: str) -> Tuple[Optional[object], Optional[Path]]:
    path = library.resolve(arg)
    if path is None:
        print(error(t("cli.not_found", arg=arg)))
        print(info(t("cli.try_list")))
        return None, None
    try:
        workout = library.load(path)
    except WorkoutLoadError as exc:
        print(error(t("cli.invalid_workout", name=path.name)))
        print(error(f"   {exc}"))
        return None, path
    return workout, path


def _ask(question: str) -> bool:
    return input(f"{question} [{t('common.yes_no')}]: ").strip().lower() in (
        "y", "yes", "s", "si", "sí"
    )


# ======================================================================
# Handlers (adaptadores finos sobre la capa de aplicación)
# ======================================================================

def cmd_list() -> int:
    files = library.library_files()
    if not files:
        print(info(t("cli.no_workouts", dir=library.LIBRARY_DIR)))
        return 0
    print(title(t("cli.list_header", n=len(files))))
    for idx, f in enumerate(files, start=1):
        print(f"  {idx:>2}) {f.name:<46} {info(library.peek_name(f))}")
    return 0


def cmd_validate(arg: str) -> int:
    workout, _ = _resolve_and_load(arg)
    if workout is None:
        return 1
    n_jobs = sum(len(s.jobs) for s in workout.stages)
    print(success(t("cli.valid", name=workout.name, stages=len(workout.stages), jobs=n_jobs)))
    return 0


def cmd_preview(arg: str, full: bool = False) -> int:
    workout, _ = _resolve_and_load(arg)
    if workout is None:
        return 1
    print(success(t("cli.preview_valid")))
    print(format_workout_v2_full(workout) if full else format_workout_v2_summary(workout))
    return 0


def cmd_run(arg: str) -> int:
    workout, path = _resolve_and_load(arg)
    if workout is None:
        return 1
    print(success(t("cli.run_ready", name=workout.name)))
    print(format_workout_v2_summary(workout))
    print()
    run_workout_v2_interactive(workout, source_path=path)
    # Standalone file (outside the library): offer to save it.
    if path is not None and not library.is_in_library(path):
        if _ask("\n" + t("cli.ask_save_library")):
            dest, replaced = library.import_workout(path)
            print(success(t("cli.saved_as", name=dest.name)
                          + (t("cli.replaced_suffix") if replaced else "")))
    return 0


def cmd_drive(arg: str) -> int:
    workout, path = _resolve_and_load(arg)
    if workout is None:
        return 1
    from src.ui.cli.player import drive_workout_v2
    drive_workout_v2(workout, source_path=path)
    return 0


def cmd_load(arg: str) -> int:
    path = library.resolve(arg)
    if path is None:
        print(error(t("cli.file_not_found", arg=arg)))
        return 1
    try:
        dest, replaced = library.import_workout(path)
    except WorkoutLoadError as exc:
        print(error(t("cli.invalid_not_saved")))
        print(error(f"   {exc}"))
        return 1
    print(success(t("cli.loaded", name=dest.name) + (t("cli.replaced_suffix") if replaced else "")))
    print(info(t("cli.run_hint", stem=dest.stem)))
    return 0


def cmd_remove(arg: str) -> int:
    path = library.remove_workout(arg)
    if path is None:
        print(error(t("cli.not_in_library", arg=arg)))
        return 1
    print(success(t("cli.removed", name=path.name)))
    return 0


def cmd_stats() -> int:
    # Sin dir explícito: agrega todas las carpetas de logs existentes (canónica + legacy),
    # resueltas en el momento, para incluir siempre lo que se acaba de escribir.
    print(build_stats_report())
    pr = build_pr_report()
    if pr:
        print(pr)
    return 0


def cmd_components(rebuild: bool = False) -> int:
    from src.application import components
    if rebuild:
        r = components.rebuild_from_library()
        print(success(t("cli.components_rebuilt", stages=r['stages'], jobs=r['jobs'])))
    stages = components.stage_names()
    jobs = components.job_names()
    print(title(t("cli.saved_stages", n=len(stages))))
    for s in stages:
        print("   · " + info(s))
    print(title("\n" + t("cli.saved_jobs", n=len(jobs))))
    for j in jobs:
        print("   · " + info(j))
    if not stages and not jobs:
        print(info("\n" + t("cli.components_empty")))
    return 0


def cmd_stages() -> int:
    from src.application import components
    stages = components.stage_names()
    print(title(t("cli.saved_stages", n=len(stages))))
    for s in stages:
        print("   · " + info(s))
    if not stages:
        print(info(t("cli.components_empty")))
    return 0


def cmd_jobs() -> int:
    from src.application import components
    jobs = components.job_names()
    print(title(t("cli.saved_jobs", n=len(jobs))))
    for j in jobs:
        print("   · " + info(j))
    if not jobs:
        print(info(t("cli.components_empty")))
    return 0


def cmd_find(tags: list) -> int:
    from src.application import components
    tags = [tg for tg in (tags or []) if tg]
    if not tags:
        print(error(t("cli.find_need_tag")))
        return 1
    workouts = library.workouts_by_tag(tags)
    stages = components.stages_by_tag(tags)
    jobs = components.jobs_by_tag(tags)
    print(title(t("cli.find_header", tags=", ".join(tags))))
    print(info("\n" + t("cli.find_workouts", n=len(workouts))))
    for _, name in workouts:
        print("   · " + info(name))
    print(info("\n" + t("cli.find_stages", n=len(stages))))
    for s in stages:
        print("   · " + info(s))
    print(info("\n" + t("cli.find_jobs", n=len(jobs))))
    for j in jobs:
        print("   · " + info(j))
    if not (workouts or stages or jobs):
        print(info("\n" + t("cli.find_none")))
    return 0


def _slugify(text: str) -> str:
    text = (text or "").strip().lower()
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in text) or "workout"


def cmd_new() -> int:
    import tempfile
    import yaml as _yaml
    from src.ui.cli.builder import build_workout_interactive
    from src.application import builder as appbuilder

    wdict = build_workout_interactive()
    if not wdict:
        print(info(t("common.cancelled")))
        return 1

    text = _yaml.safe_dump(wdict, allow_unicode=True, sort_keys=False)
    print(title(t("cli.yaml_built")))
    print(text)

    err = appbuilder.validate_workout_dict(wdict, library.SCHEMA_ROOT)
    if err:
        print(error(t("cli.not_valid_yet")))
        print(error(f"   {err}"))
        if _ask(t("cli.ask_draft")):
            out = Path.cwd() / f"{_slugify(wdict.get('name', 'draft'))}.draft.yaml"
            out.write_text(text, encoding="utf-8")
            print(success(t("cli.draft_saved", name=out.name)))
        return 1

    print(success(t("cli.valid_short")))
    if _ask(t("cli.ask_save_library")):
        tmp = Path(tempfile.gettempdir()) / f"{_slugify(wdict.get('name', 'workout'))}.yaml"
        tmp.write_text(text, encoding="utf-8")
        dest, replaced = library.import_workout(tmp)
        try:
            tmp.unlink()
        except Exception:
            pass
        print(success(t("cli.saved_library", name=dest.name)
                      + (t("cli.replaced_suffix") if replaced else "")))
        print(info(t("cli.saved_components_note")))
    return 0


# ======================================================================
# CLI
# ======================================================================

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rawtrainer",
        description="RawTrainer — a CLI workout player.",
    )
    parser.add_argument("--debug", action="store_true", help="Debug logging.")
    parser.add_argument("--log-file", type=Path, default=None, help="Optional log file.")

    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", aliases=["run-v2"], help="Validate, show and run a workout.")
    p_run.add_argument("workout", help="Path, name or number (see 'list').")

    p_drive = sub.add_parser("drive", help="Run the workout with timers (driven mode).")
    p_drive.add_argument("workout", help="Path, name or number.")

    p_prev = sub.add_parser("preview", aliases=["preview-v2"], help="Validate and show a workout (without running).")
    p_prev.add_argument("workout", help="Path, name or number.")
    p_prev.add_argument("--full", action="store_true", help="Full detail (exercises, times, rests).")

    p_val = sub.add_parser("validate", help="Only validate a workout (exit 0/1).")
    p_val.add_argument("workout", help="Path, name or number.")

    p_load = sub.add_parser("load", aliases=["import"], help="Validate a file and save it to your library.")
    p_load.add_argument("workout", help="Path to a YAML file.")

    p_rm = sub.add_parser("remove", aliases=["rm"], help="Remove a workout from your library.")
    p_rm.add_argument("workout", help="Name or number.")

    sub.add_parser("list", help="List the workouts in your library.")
    sub.add_parser("stats", aliases=["stats-v2"], help="Stats for your sessions.")
    p_comp = sub.add_parser("components", aliases=["comp"], help="List reusable stages and jobs.")
    p_comp.add_argument("--rebuild", action="store_true", help="Rebuild from your workout library.")
    p_find = sub.add_parser("find", aliases=["search"], help="Find workouts/stages/jobs by tag(s).")
    p_find.add_argument("tags", nargs="+", help="One or more tags.")
    sub.add_parser("new", aliases=["build"], help="Wizard to build a workout from scratch.")
    sub.add_parser("menu", help="Interactive terminal menu (default with no subcommand).")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    configure_logging(
        debug=getattr(args, "debug", False),
        log_file=getattr(args, "log_file", None),
    )
    log.debug("CLI args: %r", args)

    cmd = args.command
    try:
        if cmd in ("run", "run-v2"):
            return cmd_run(args.workout)
        if cmd == "drive":
            return cmd_drive(args.workout)
        if cmd in ("preview", "preview-v2"):
            return cmd_preview(args.workout, full=getattr(args, "full", False))
        if cmd == "validate":
            return cmd_validate(args.workout)
        if cmd in ("load", "import"):
            return cmd_load(args.workout)
        if cmd in ("remove", "rm"):
            return cmd_remove(args.workout)
        if cmd == "list":
            return cmd_list()
        if cmd in ("stats", "stats-v2"):
            return cmd_stats()
        if cmd in ("components", "comp"):
            return cmd_components(rebuild=getattr(args, "rebuild", False))
        if cmd in ("find", "search"):
            return cmd_find(args.tags)
        if cmd in ("new", "build"):
            return cmd_new()
        if cmd == "menu":
            from src.ui.cli.menu import menu_loop
            return menu_loop()
        # sin subcomando -> menú interactivo de terminal
        from src.ui.cli.menu import menu_loop
        return menu_loop()
    except (KeyboardInterrupt, EOFError):
        print(info(t("common.cancelled")))
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
