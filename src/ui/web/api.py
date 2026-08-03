# src/ui/web/api.py
"""FastAPI: la GUI móvil/tablet sobre la MISMA capa de aplicación que la CLI.

    uvicorn src.ui.web.api:app --host 0.0.0.0 --port 8000 --reload

Nada de lógica de entrenamiento vive aquí: los segmentos los construye
`src/application/driven/executors.py` y las sesiones las escribe
`src/infrastructure/run_log.py`, así que `stats-v2` en terminal cuenta también
las sesiones hechas desde el móvil.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.application import library
from src.application.workout_loader import WorkoutLoadError
from src.infrastructure import run_log
from src.infrastructure import data_scope
from src.ui.web import cf_access
from src.ui.web import errors
from src.ui.web import schema_hints
from src.ui.web.serializers import build_timeline, workout_to_dict

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="RawTrainer", version="2.0")


class AccessScopeMiddleware:
    """Per-request per-user data scope from a verified Cloudflare Access identity.

    Local mode (no CF_ACCESS_* env): pass-through, app uses the global data
    location exactly as before. Access mode: every request must carry a valid
    Cf-Access-Jwt-Assertion; its verified email scopes all data access to that
    user for the request. No valid identity -> 403 (never trust an unverified header).
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not cf_access.access_enabled():
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1")
                   for k, v in scope.get("headers") or []}
        token = headers.get("cf-access-jwt-assertion") or _cookie(headers.get("cookie", ""), "CF_Authorization")
        email = cf_access.email_from_token(token)
        if not email:
            return await _forbidden(send)
        ctx = data_scope.set_root(data_scope.user_root(email))
        try:
            await self.app(scope, receive, send)
        finally:
            data_scope.reset(ctx)


def _cookie(cookie_header: str, name: str):
    for part in (cookie_header or "").split(";"):
        k, _, v = part.strip().partition("=")
        if k == name:
            return v
    return None


async def _forbidden(send):
    await send({"type": "http.response.start", "status": 403,
                "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
    await send({"type": "http.response.body",
                "body": b"403 - Cloudflare Access identity required"})


app.add_middleware(AccessScopeMiddleware)


# ---------------------------------------------------------------------------
# Library
# ---------------------------------------------------------------------------

def _entry(path: Path) -> Dict[str, Any]:
    return {"id": path.stem, "file": path.name, "name": library.peek_name(path)}


@app.get("/api/library")
def api_library() -> List[Dict[str, Any]]:
    """Los YAML de data/workouts_files, en el mismo orden que el menú."""
    out = []
    for path in library.library_files():
        item = _entry(path)
        try:
            workout = library.load(path)
            item["n_stages"] = len(workout.stages)
            item["n_jobs"] = sum(len(s.jobs) for s in workout.stages)
            item["valid"] = True
        except WorkoutLoadError as exc:
            item.update({"valid": False, "error": str(exc), "n_stages": 0, "n_jobs": 0})
        out.append(item)
    return out


def _load_or_404(wid: str):
    path = library.resolve(wid)
    if path is None:
        raise HTTPException(status_code=404, detail=f"not found: {wid}")
    try:
        return library.load(path), path
    except WorkoutLoadError as exc:
        message, _ = errors.clean_validation_error(exc)
        raise HTTPException(status_code=422, detail=message)


@app.get("/api/workouts/{wid}")
def api_workout(wid: str) -> Dict[str, Any]:
    workout, path = _load_or_404(wid)
    return {"id": path.stem, "file": path.name, "workout": workout_to_dict(workout)}


@app.get("/api/workouts/{wid}/timeline")
def api_timeline(wid: str, driven: bool = True) -> Dict[str, Any]:
    """Segmentos cronometrados listos para reproducir (build_segments por job)."""
    workout, path = _load_or_404(wid)
    return {
        "id": path.stem,
        "file": path.name,
        "workout": workout_to_dict(workout),
        "driven": driven,
        "timeline": build_timeline(workout, driven=driven),
    }


@app.delete("/api/workouts/{wid}")
def api_remove(wid: str) -> Dict[str, Any]:
    path = library.remove_workout(wid)
    if path is None:
        raise HTTPException(status_code=404, detail=f"not in library: {wid}")
    return {"removed": path.name}


@app.post("/api/import")
async def api_import(request: Request) -> Dict[str, Any]:
    """Valida y guarda en la biblioteca. Acepta multipart (campo `file`) o JSON {"text","filename"}.

    Se parsea a mano según Content-Type: FastAPI no deja mezclar un File() con un
    body JSON en el mismo endpoint (un File fuerza multipart y el JSON del pegado
    se perdía → 400). Reutiliza library.import_workout: valida ANTES de copiar.
    """
    ctype = request.headers.get("content-type", "")
    filename: Optional[str] = None
    content: Optional[bytes] = None

    if ctype.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if upload is not None and hasattr(upload, "read"):
            filename = Path(getattr(upload, "filename", None) or "upload.yaml").name
            content = await upload.read()
    else:
        try:
            payload = await request.json()
        except Exception:
            payload = None
        if isinstance(payload, dict) and payload.get("text"):
            name = Path(str(payload.get("filename") or "pasted.yaml")).name
            if not name.endswith((".yaml", ".yml")):
                name += ".yaml"
            filename = name
            content = str(payload["text"]).encode("utf-8")

    if content is None or not filename:
        raise HTTPException(status_code=400, detail="send a file or {'text': ...}")

    tmp_dir = Path(tempfile.mkdtemp(prefix="rawtrainer_import_"))
    try:
        tmp = tmp_dir / filename
        tmp.write_bytes(content)
        try:
            dest, replaced = library.import_workout(tmp)
        except WorkoutLoadError as exc:
            message, _ = errors.clean_validation_error(exc, content.decode("utf-8", "replace"))
            raise HTTPException(status_code=422, detail=message)

        workout = library.load(dest)
        return {
            "id": dest.stem,
            "file": dest.name,
            "replaced": replaced,
            "workout": workout_to_dict(workout),
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/api/validate")
def api_validate(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Valida sin guardar (JSON Schema v2 + dominio), como `validate` en la CLI."""
    text = str(payload.get("text") or "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="empty")
    tmp_dir = Path(tempfile.mkdtemp(prefix="rawtrainer_check_"))
    try:
        tmp = tmp_dir / "check.yaml"
        tmp.write_text(text, encoding="utf-8")
        try:
            workout = library.load(tmp)
        except WorkoutLoadError as exc:
            message, detail = errors.clean_validation_error(exc, text)
            return {"valid": False, "error": message, "detail": detail}
        return {"valid": True, "workout": workout_to_dict(workout)}
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

@app.post("/api/runs")
def api_save_run(record: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Guarda una sesión en .run_logs_v2 con el formato de run_log.py."""
    if not record.get("workout_name"):
        raise HTTPException(status_code=400, detail="workout_name required")
    # Idempotencia: el cliente reintenta los guardados que fallan (wifi de gimnasio),
    # marcándolos con client_id. Si ya existe una sesión con ese id, no la dupliques.
    cid = record.get("client_id")
    if cid and any(r.get("client_id") == cid for r in run_log.load_all_records()):
        return {"saved": "duplicate", "duplicate": True}
    record.setdefault("version", 2)
    record.setdefault("session_mode", "driven")
    record.setdefault("started_at", run_log.now_iso())
    record["ended_at"] = record.get("ended_at") or run_log.now_iso()
    target = run_log.save_run_record(record)
    return {"saved": target.name}


@app.get("/api/runs")
def api_runs() -> List[Dict[str, Any]]:
    return run_log.load_all_records()


@app.get("/api/stats")
def api_stats() -> Dict[str, Any]:
    """Agregado por workout + PRs, a partir de los mismos run logs que stats-v2."""
    records = run_log.load_all_records()
    by_workout: Dict[str, Dict[str, Any]] = {}
    for rec in records:
        name = rec.get("workout_name") or "?"
        agg = by_workout.setdefault(name, {"workout": name, "sessions": 0,
                                           "total_seconds": 0, "last": None})
        agg["sessions"] += 1
        agg["total_seconds"] += int(rec.get("duration_seconds") or 0)
        stamp = rec.get("ended_at") or rec.get("started_at")
        if stamp and (agg["last"] is None or stamp > agg["last"]):
            agg["last"] = stamp

    prs: Dict[str, Dict[str, Any]] = {}
    scores = (
        ("result_rounds", True, "rounds"),
        ("result_total_reps", True, "reps"),
        ("result_time_seconds", False, "seconds"),
    )
    for rec in records:
        for stage in rec.get("stages") or []:
            for job in stage.get("jobs") or []:
                for key, higher, unit in scores:
                    value = job.get(key)
                    if not isinstance(value, (int, float)):
                        continue
                    pid = f"{rec.get('workout_name')}|{job.get('name')}|{key}"
                    pr = prs.setdefault(pid, {
                        "workout": rec.get("workout_name"), "job": job.get("name"),
                        "mode": job.get("mode"), "key": key, "unit": unit,
                        "higher_better": higher, "best": None, "attempts": 0,
                    })
                    pr["attempts"] += 1
                    if pr["best"] is None or (value > pr["best"] if higher else value < pr["best"]):
                        pr["best"] = value

    return {
        "sessions": len(records),
        "total_seconds": sum(int(r.get("duration_seconds") or 0) for r in records),
        "by_workout": sorted(by_workout.values(), key=lambda a: -a["sessions"]),
        "prs": sorted(prs.values(), key=lambda p: (p["workout"] or "", p["job"] or "")),
    }


# ---------------------------------------------------------------------------
# Static app
# ---------------------------------------------------------------------------

@app.get("/api/schema")
def api_schema() -> Dict[str, Any]:
    """Key/required map distilled from the JSON Schemas, for the editor autocomplete.
    Single source of truth — stays in sync with validation because it reads the schemas."""
    try:
        return schema_hints.build_hints(library.SCHEMA_ROOT)
    except Exception as exc:  # never take the app down for a hint failure
        raise HTTPException(status_code=500, detail=f"schema hints unavailable: {exc}")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/manifest.webmanifest")
def manifest() -> FileResponse:
    """Served explicitly so it gets the right content type (StaticFiles guesses)."""
    return FileResponse(STATIC_DIR / "manifest.webmanifest",
                        media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker() -> FileResponse:
    """Root-scoped (so it controls the whole app) and never cached, so clients
    revalidate and pick up a new worker on each deploy."""
    return FileResponse(
        STATIC_DIR / "sw.js",
        media_type="text/javascript",
        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"},
    )


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
