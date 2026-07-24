# rawtrainer_prettyprint/ci_strict.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

class PrettyPrintKeyCollision(ValueError):
    pass

def _norm(k: str) -> str:
    return k.casefold()

@dataclass
class CIDictStrict:
    """
    Read-only mapping view with case-insensitive lookup.
    STRICT collisions: if two keys collide under casefold(), we raise.
    """
    raw: Mapping[str, Any]
    path: str

    _index: dict[str, str] | None = None

    def _build_index(self) -> dict[str, str]:
        if self._index is not None:
            return self._index

        idx: dict[str, str] = {}
        collisions: dict[str, list[str]] = {}

        for ok in self.raw.keys():
            nk = _norm(ok)
            if nk in idx and idx[nk] != ok:
                collisions.setdefault(nk, [idx[nk]]).append(ok)
            else:
                idx[nk] = ok

        if collisions:
            details = ", ".join(f"{k!r}: {v}" for k, v in collisions.items())
            raise PrettyPrintKeyCollision(
                f"[prettyprint] Case-insensitive key collision at {self.path}. Conflicts: {details}. "
                f"Fix: keep only ONE casing per field in that object."
            )

        self._index = idx
        return self._index

    def has(self, key: str) -> bool:
        if key in self.raw:
            return True
        return _norm(key) in self._build_index()

    def get(self, key: str, default: Any = None) -> Any:
        if key in self.raw:
            return self.raw[key]
        ok = self._build_index().get(_norm(key))
        if ok is None:
            return default
        return self.raw.get(ok, default)

def ci_get(node: Any, key: str, path: str, default: Any = None) -> Any:
    if not isinstance(node, Mapping):
        return default
    return CIDictStrict(node, path).get(key, default)

def ci_get_list(node: Any, key: str, path: str) -> list[Any]:
    v = ci_get(node, key, path, default=None)
    if v is None:
        return []
    if isinstance(v, list):
        return v
    raise TypeError(f"[prettyprint] Expected list at {path}.{key}, got {type(v).__name__}")

def ci_get_str(node: Any, key: str, path: str, default: str = "") -> str:
    v = ci_get(node, key, path, default=None)
    if v is None:
        return default
    return str(v)