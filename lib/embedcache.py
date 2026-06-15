"""Redis-backed embedding cache (additive, multi-worker safe).

The JSONL cache in :mod:`lib.embed` is a plain append-only file: under more
than one worker its concurrent `open("a")` writes can interleave and corrupt
rows. This module swaps in Redis when ``REDIS_URL`` is set and reachable —
atomic `MSET`/`SETEX`, O(1) `MGET` — and otherwise returns ``None`` so callers
fall back to the existing JSONL path. Same additive contract as ``db/``.

    REDIS_URL=redis://localhost:6379/0   # enables the cache
    EMBED_CACHE_TTL_DAYS=0               # 0 = keep forever

Values are JSON-encoded float lists keyed by the same sha1 ``lib.embed`` uses,
so a Redis cache and a JSONL cache never collide and either can be rebuilt.
"""
from __future__ import annotations

import json
import logging
import os

try:  # optional dep: absent → cache stays disabled, JSONL path used
    import redis
except ImportError:  # pragma: no cover - exercised only without the extra
    redis = None  # type: ignore[assignment]

log = logging.getLogger("pulsetrace.embedcache")


class RedisEmbedCache:
    PREFIX = "emb:"

    def __init__(self, client, ttl_seconds: int = 0) -> None:
        self._r = client
        self._ttl = max(0, ttl_seconds)

    def get_many(self, keys: list[str]) -> dict[str, list[float]]:
        if not keys:
            return {}
        raw = self._r.mget([self.PREFIX + k for k in keys])
        out: dict[str, list[float]] = {}
        for k, v in zip(keys, raw):
            if v is None:
                continue
            try:
                out[k] = json.loads(v)
            except (ValueError, TypeError):
                continue
        return out

    def put_many(self, rows: list[tuple[str, list[float]]]) -> None:
        if not rows:
            return
        mapping = {self.PREFIX + k: json.dumps(v) for k, v in rows}
        if self._ttl:
            pipe = self._r.pipeline()
            for rk, val in mapping.items():
                pipe.setex(rk, self._ttl, val)
            pipe.execute()
        else:
            self._r.mset(mapping)


_cache: RedisEmbedCache | None = None
_resolved = False


def reset_embed_cache() -> None:
    """Drop the memoised backend — re-resolves env on next call (tests/reload)."""
    global _cache, _resolved
    _cache, _resolved = None, False


def get_embed_cache() -> RedisEmbedCache | None:
    """Process-wide singleton. ``None`` means 'use the JSONL fallback'."""
    global _cache, _resolved
    if _resolved:
        return _cache
    _resolved = True

    url = (os.environ.get("REDIS_URL") or "").strip()
    if not url:
        return None
    if redis is None:
        log.warning("REDIS_URL set but redis-py not installed; using JSONL cache")
        return None
    try:
        client = redis.from_url(url, decode_responses=True)
        client.ping()
    except redis.exceptions.RedisError as exc:
        log.warning("Redis embed cache unreachable (%s); using JSONL cache", exc)
        return None

    ttl = int(os.environ.get("EMBED_CACHE_TTL_DAYS", "0") or 0) * 86400
    _cache = RedisEmbedCache(client, ttl_seconds=ttl)
    log.info("Redis embed cache active (ttl_days=%s)", ttl // 86400 if ttl else 0)
    return _cache
