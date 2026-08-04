#!/usr/bin/env python3
"""Admin CLI — manage per-user workout libraries (beta ops, before coach mode).

Push / list / inspect workouts in ANY user's library, keyed by their login email —
the same per-user data root the web app already uses behind Cloudflare Access
(src/infrastructure/data_scope.py + src/application/library.py). No new storage and
no user-type model: you supply the email, this scopes to that user and reuses the
app's own *validated* import — invalid YAML is refused and nothing is copied.

Run from the repo root, with the same Python you run uvicorn with:

  python manage_libraries.py push  --to tester@example.com --file ./murph.yaml
  python manage_libraries.py push  --to tester@example.com --file ./m.yaml --as murph
  python manage_libraries.py ls    --to tester@example.com
  python manage_libraries.py users
  python manage_libraries.py path  --to tester@example.com

A user's library is <project>/data/users/<key>/workouts_files/, where <key> is a
slug+hash of their email (data_scope.user_key). `push`/`ls`/`path` remember the
emails you use in <project>/data/known_emails.txt so `users` can label the on-disk
libraries with the exact email instead of a guessed slug.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # make `src...` importable from repo root

from src.infrastructure import data_scope


def _data_dir() -> Path:
    """<project_root>/data — user_root is <project>/data/users/<key>, so go up two."""
    return data_scope.user_root("_").parents[1]


def _roster() -> Path:
    return _data_dir() / "known_emails.txt"


def _remember(email: str) -> None:
    """Record an email so `users` can label its on-disk library exactly later."""
    email = (email or "").strip().lower()
    if not email:
        return
    r = _roster()
    seen = set(r.read_text(encoding="utf-8").split()) if r.exists() else set()
    if email not in seen:
        r.parent.mkdir(parents=True, exist_ok=True)
        with r.open("a", encoding="utf-8") as fh:
            fh.write(email + "\n")


def cmd_push(args) -> None:
    from src.application import library
    from src.application.workout_loader import WorkoutLoadError
    src = Path(args.file).expanduser()
    if not src.is_file():
        sys.exit(f"x  no such file: {src}")
    _remember(args.to)
    tmp_dir = None
    try:
        push_src = src
        if args.as_name:  # rename on the way in (library filename = source filename otherwise)
            name = args.as_name if args.as_name.endswith((".yaml", ".yml")) else args.as_name + ".yaml"
            tmp_dir = Path(tempfile.mkdtemp(prefix="rt_admin_"))
            push_src = tmp_dir / Path(name).name
            shutil.copy2(src, push_src)
        with data_scope.use_root(data_scope.user_root(args.to)):
            dest, replaced = library.import_workout(push_src)  # validates first; raises if invalid
        print(f"OK {'replaced' if replaced else 'added'}  {dest.name}  ->  {args.to}")
        print(f"   {dest}")
    except WorkoutLoadError as exc:
        sys.exit(f"x  invalid workout — nothing written:\n{exc}")
    finally:
        if tmp_dir:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def cmd_ls(args) -> None:
    from src.application import library
    _remember(args.to)
    with data_scope.use_root(data_scope.user_root(args.to)):
        rows = [(p.name, library.peek_name(p)) for p in library.library_files()]
    if not rows:
        print(f"(empty)  {args.to}")
        return
    w = max(len(f) for f, _ in rows)
    print(f"{len(rows)} workout(s) for {args.to}:")
    for fn, name in rows:
        print(f"  {fn.ljust(w)}  {name}")


def cmd_path(args) -> None:
    _remember(args.to)
    print(data_scope.user_root(args.to) / "workouts_files")


def cmd_users(args) -> None:
    users_dir = _data_dir() / "users"
    if not users_dir.is_dir():
        print("no user libraries yet (no one has logged in or been pushed to)")
        return
    known = {}
    if _roster().exists():
        for e in _roster().read_text(encoding="utf-8").split():
            known[data_scope.user_key(e)] = e
    dirs = sorted(p for p in users_dir.iterdir() if p.is_dir())
    print(f"{len(dirs)} user librar(y/ies) under {users_dir}:")
    for d in dirs:
        wf = d / "workouts_files"
        n = len(list(wf.glob("*.yaml")) + list(wf.glob("*.yml"))) if wf.is_dir() else 0
        label = known.get(d.name) or f"?  (slug: {d.name.rsplit('-', 1)[0]})"
        print(f"  {n:3d} workouts   {label}")


def main() -> None:
    p = argparse.ArgumentParser(description="Manage per-user workout libraries (admin / beta ops).")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("push", help="validate + add a workout YAML to a user's library")
    sp.add_argument("--to", required=True, metavar="EMAIL")
    sp.add_argument("--file", required=True, metavar="PATH")
    sp.add_argument("--as", dest="as_name", metavar="NAME", help="library filename (default: source filename)")
    sp.set_defaults(fn=cmd_push)

    sp = sub.add_parser("ls", help="list a user's library")
    sp.add_argument("--to", required=True, metavar="EMAIL")
    sp.set_defaults(fn=cmd_ls)

    sp = sub.add_parser("path", help="print a user's library directory")
    sp.add_argument("--to", required=True, metavar="EMAIL")
    sp.set_defaults(fn=cmd_path)

    sp = sub.add_parser("users", help="list all user libraries (labels emails you've used)")
    sp.set_defaults(fn=cmd_users)

    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
