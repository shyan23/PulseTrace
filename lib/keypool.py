"""Gemini API-key pool with quota failover.

Holds the primary key (`GEMINI_API_KEY`) plus any backups
(`GEMINI_BACKUP_KEY`, comma- or newline-separated) and a process-global
pointer. When a call hits a quota/429 error the caller advances the pointer once,
so every later call in this worker uses the next live key instead of re-hitting
the exhausted one each time.
"""
from __future__ import annotations
import os
import threading

_LOCK = threading.Lock()
_idx = 0


def _clean(v: str) -> str:
    return v.strip().strip('"').strip("'")


def gemini_keys() -> list[str]:
    raw = [os.environ.get("GEMINI_API_KEY", "")]
    backup = os.environ.get("GEMINI_BACKUP_KEY", "")
    raw += backup.replace("\n", ",").split(",")
    out: list[str] = []
    for v in raw:
        v = _clean(v)
        if v and v not in out:
            out.append(v)
    return out


def current_gemini_key() -> str:
    ks = gemini_keys()
    if not ks:
        return "EMPTY"
    with _LOCK:
        return ks[min(_idx, len(ks) - 1)]


def advance_gemini_key() -> bool:
    """Switch to the next backup key. Returns True if a new key became active."""
    global _idx
    ks = gemini_keys()
    with _LOCK:
        if _idx < len(ks) - 1:
            _idx += 1
            return True
        return False


def reset() -> None:
    global _idx
    with _LOCK:
        _idx = 0


def is_quota_error(exc: Exception) -> bool:
    code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if code == 429:
        return True
    s = str(exc).lower()
    return (
        "429" in s
        or "resource_exhausted" in s
        or "spending cap" in s
        or "quota" in s
        or "rate limit" in s
        or "insufficient" in s and "quota" in s
    )
