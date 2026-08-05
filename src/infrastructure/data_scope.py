# src/infrastructure/data_scope.py
"""Request-scoped data-root override for per-user isolation behind Cloudflare Access.

The CLI and the local (no-login) path never set an override, so the app resolves
data exactly as before: the global ``data/`` library, registry and ``.run_logs_v2/``.
The web layer, when a request carries a *verified* Cloudflare Access identity, sets
a per-user root for the duration of that request only, so each beta tester gets an
isolated library, registry and run log.

Design note: this is deliberately a thin override rather than a rewrite. Every path
helper in library.py / workout_registry.py / run_log.py falls back to its previous
computation when ``override()`` is None — which keeps every existing test (that
monkeypatches ``LIBRARY_DIR`` or ``_project_root``) working unchanged.
"""
from __future__ import annotations

import hashlib
import re
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator, Optional

# None  -> global/default location (CLI, local use, tests).
# Path  -> per-user data root, e.g. <project_root>/data/users/<key>.
_override: ContextVar[Optional[Path]] = ContextVar("rt_data_root", default=None)


def override() -> Optional[Path]:
    """The active per-user data root, or None for the global/default location."""
    return _override.get()


def set_root(path: Optional[Path]):
    """Set the active per-user data root; returns a token to pass to ``reset()``."""
    return _override.set(path)


def reset(token) -> None:
    """Restore the previous data root (pair with ``set_root``)."""
    _override.reset(token)


# Verified caller identity for the active request (e.g. {"email": ...}), or None for the
# CLI / local (no-login) path / tests. Set by the web middleware once Cloudflare Access has
# verified the JWT, so handlers can authorize (admin endpoints) without re-parsing headers.
_identity: ContextVar[Optional[dict]] = ContextVar("rt_identity", default=None)


def current_identity() -> Optional[dict]:
    """The verified identity for the active request, or None (CLI / local mode / tests)."""
    return _identity.get()


def set_identity(value: Optional[dict]):
    """Set the request identity; returns a token to pass to ``reset_identity()``."""
    return _identity.set(value)


def reset_identity(token) -> None:
    _identity.reset(token)


@contextmanager
def use_root(path: Optional[Path]) -> Iterator[None]:
    """Scope a block of code to a data root (used by tests and any sync caller)."""
    token = _override.set(path)
    try:
        yield
    finally:
        _override.reset(token)


def user_key(identity: str) -> str:
    """Filesystem-safe, stable key for a user identity (usually an email).

    slug + short sha256 so that two identities that slug to the same string
    (e.g. ``a.b@x.com`` and ``a-b@x.com``) never collide on disk.
    """
    ident = (identity or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ident).strip("-")[:40] or "user"
    digest = hashlib.sha256(ident.encode("utf-8")).hexdigest()[:10]
    return f"{slug}-{digest}"


def _project_root() -> Path:
    # Lazy import: honours tests that monkeypatch workout_registry._project_root,
    # and avoids an import cycle (workout_registry imports this module).
    from src.infrastructure.workout_registry import _project_root as _pr
    return _pr()


def user_root(identity: str) -> Path:
    """Per-user data root under ``<project_root>/data/users/<key>``."""
    return _project_root() / "data" / "users" / user_key(identity)
