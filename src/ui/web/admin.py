# src/ui/web/admin.py
"""Admin console + API — manage any user's workout library from the browser.

A thin, RT_ADMINS-gated layer over the app's existing per-user data model
(``data_scope`` + ``library``): list users, view a user's library, and push a
validated workout into it. No user-type model yet — you target a user by the
email they log in with, exactly like the ``manage_libraries.py`` CLI.

Auth (mirrors the rest of the app):
* **Local mode** (no ``CF_ACCESS_*`` env) — no login, full access, same as the app.
* **Access mode** — the request already carries a Cloudflare-Access-verified email
  (stashed by the web middleware); it must be listed in ``RT_ADMINS`` (comma-separated)
  to reach any ``/api/admin/*`` route or the ``/admin`` page.

``library`` (and its heavy domain deps) is imported lazily inside the handlers so
this module — and its pure helpers — import cleanly anywhere.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse, Response

from src.infrastructure import data_scope
from src.ui.web import cf_access

router = APIRouter()
STATIC_DIR = Path(__file__).parent / "static"


# ── auth ────────────────────────────────────────────────────────────────────
def admin_emails() -> set:
    return {e.strip().lower() for e in os.environ.get("RT_ADMINS", "").split(",") if e.strip()}


def is_admin(email: Optional[str]) -> bool:
    return bool(email) and email.strip().lower() in admin_emails()


def require_admin() -> None:
    """Allow in local mode (no login); in Access mode require an RT_ADMINS email."""
    if not cf_access.access_enabled():
        return
    ident = data_scope.current_identity() or {}
    if not is_admin(ident.get("email")):
        raise HTTPException(status_code=403, detail="admin only")


# ── users roster (global, cross-user) ───────────────────────────────────────
def _data_dir() -> Path:
    """<project_root>/data — user_root is <project>/data/users/<key>, so go up two."""
    return data_scope.user_root("_").parents[1]


def _roster_emails() -> List[str]:
    r = _data_dir() / "known_emails.txt"
    return r.read_text(encoding="utf-8").split() if r.exists() else []


def _remember(email: str) -> None:
    """Record an email so `users` can label its on-disk library exactly (shared with the CLI)."""
    email = (email or "").strip().lower()
    if not email:
        return
    r = _data_dir() / "known_emails.txt"
    seen = set(r.read_text(encoding="utf-8").split()) if r.exists() else set()
    if email not in seen:
        r.parent.mkdir(parents=True, exist_ok=True)
        with r.open("a", encoding="utf-8") as fh:
            fh.write(email + "\n")


def list_users() -> List[Dict[str, Any]]:
    users_dir = _data_dir() / "users"
    known = {data_scope.user_key(e): e for e in _roster_emails()}
    out: List[Dict[str, Any]] = []
    if users_dir.is_dir():
        for d in sorted(p for p in users_dir.iterdir() if p.is_dir()):
            wf = d / "workouts_files"
            n = len(list(wf.glob("*.yaml")) + list(wf.glob("*.yml"))) if wf.is_dir() else 0
            out.append({"key": d.name, "email": known.get(d.name), "n_workouts": n})
    return out


# ── routes ──────────────────────────────────────────────────────────────────
@router.get("/api/me")
def api_me() -> Dict[str, Any]:
    """Who am I + am I an admin — lets the client show/hide the console."""
    email = (data_scope.current_identity() or {}).get("email")
    return {"email": email, "access": cf_access.access_enabled(),
            "is_admin": (not cf_access.access_enabled()) or is_admin(email)}


@router.get("/api/admin/users")
def api_admin_users() -> List[Dict[str, Any]]:
    require_admin()
    return list_users()


@router.get("/api/admin/library")
def api_admin_library(email: str) -> List[Dict[str, Any]]:
    require_admin()
    from src.application import library
    from src.application.workout_loader import WorkoutLoadError
    _remember(email)
    out: List[Dict[str, Any]] = []
    with data_scope.use_root(data_scope.user_root(email)):
        for path in library.library_files():
            item: Dict[str, Any] = {"id": path.stem, "file": path.name, "name": library.peek_name(path)}
            try:
                wk = library.load(path)
                item.update(n_stages=len(wk.stages), n_jobs=sum(len(s.jobs) for s in wk.stages), valid=True)
            except WorkoutLoadError as exc:
                item.update(valid=False, error=str(exc), n_stages=0, n_jobs=0)
            out.append(item)
    return out


@router.post("/api/admin/push")
def api_admin_push(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Validate a workout and add it to `email`'s library (creates the library if new)."""
    require_admin()
    from src.application import library
    from src.application.workout_loader import WorkoutLoadError
    from src.ui.web import errors
    email = str(payload.get("email") or "").strip()
    text = str(payload.get("text") or "")
    if "@" not in email:
        raise HTTPException(status_code=400, detail="a valid target email is required")
    if not text.strip():
        raise HTTPException(status_code=400, detail="empty workout")
    name = Path(str(payload.get("filename") or "workout.yaml")).name
    if not name.endswith((".yaml", ".yml")):
        name += ".yaml"
    _remember(email)
    tmp_dir = Path(tempfile.mkdtemp(prefix="rt_admin_"))
    try:
        tmp = tmp_dir / name
        tmp.write_text(text, encoding="utf-8")
        try:
            with data_scope.use_root(data_scope.user_root(email)):
                dest, replaced = library.import_workout(tmp)   # validates first; nothing written if invalid
                wk = library.load(dest)
        except WorkoutLoadError as exc:
            message, _ = errors.clean_validation_error(exc, text)
            raise HTTPException(status_code=422, detail=message)
        return {"email": email, "file": dest.name, "replaced": replaced,
                "workout": {"name": wk.name, "n_stages": len(wk.stages),
                            "n_jobs": sum(len(s.jobs) for s in wk.stages)}}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.get("/admin")
def admin_page() -> Response:
    """The console page itself — gated in Access mode so only admins can load it."""
    if cf_access.access_enabled():
        ident = data_scope.current_identity() or {}
        if not is_admin(ident.get("email")):
            return Response("403 — admin only", status_code=403, media_type="text/plain; charset=utf-8")
    return FileResponse(STATIC_DIR / "admin.html")
