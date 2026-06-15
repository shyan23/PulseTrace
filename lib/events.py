"""Per-run event bus for SSE streaming.

Default is an in-process bus (one worker). When ``REDIS_URL`` is set and
reachable the factory returns a :class:`RedisEventBus` that fans events through
a Redis pub/sub channel, so a run executing on one gunicorn worker reaches an
SSE client pinned to a different worker. Both expose the same
``publish / subscribe / close`` surface, so callers never change.
"""
from __future__ import annotations
import json
import logging
import os
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("pulsetrace.events")

_LOG_DIR = Path(os.environ.get("PT_EVENT_LOG_DIR", "data/event_logs"))
_MIRROR_STDOUT = os.environ.get("PT_EVENT_QUIET", "0") != "1"


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, list[queue.Queue]] = {}
        self._lock = threading.Lock()
        self._log_handles: dict[str, Any] = {}

    def publish(self, run_id: str, event: dict[str, Any]) -> None:
        self._mirror(run_id, event)
        self._deliver_local(run_id, event)

    def _deliver_local(self, run_id: str, event: dict[str, Any]) -> None:
        with self._lock:
            qs = list(self._queues.get(run_id, []))
        for q in qs:
            try:
                q.put_nowait(event)
            except queue.Full:
                pass

    def _mirror(self, run_id: str, event: dict[str, Any]) -> None:
        line = f"[ev {run_id} {event.get('type', '?')}] {json.dumps(event, default=str)}"
        if _MIRROR_STDOUT:
            print(line, file=sys.stdout, flush=True)
        try:
            with self._lock:
                fh = self._log_handles.get(run_id)
                if fh is None:
                    _LOG_DIR.mkdir(parents=True, exist_ok=True)
                    fh = open(_LOG_DIR / f"{run_id}.log", "a", buffering=1)
                    self._log_handles[run_id] = fh
            ts = time.strftime("%H:%M:%S")
            fh.write(f"{ts} {line}\n")
        except Exception:
            pass

    def subscribe(self, run_id: str) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=1024)
        with self._lock:
            self._queues.setdefault(run_id, []).append(q)
        return q

    def close(self, run_id: str) -> None:
        self._deliver_local(run_id, {"type": "_close"})
        self._drop(run_id)

    def _drop(self, run_id: str) -> None:
        with self._lock:
            self._queues.pop(run_id, None)
            fh = self._log_handles.pop(run_id, None)
        if fh:
            try:
                fh.close()
            except Exception:
                pass


class RedisEventBus(EventBus):
    """Cross-process bus. Publishes to ``pt:events:<run_id>``; a process-wide
    pattern listener delivers every message (including its own) into the local
    subscriber queues — so delivery is identical whether the publisher and the
    SSE reader share a worker or not."""

    CHANNEL = "pt:events:"

    def __init__(self, client) -> None:
        super().__init__()
        self._r = client
        pubsub = self._r.pubsub(ignore_subscribe_messages=True)
        pubsub.psubscribe(**{self.CHANNEL + "*": self._on_message})
        self._thread = pubsub.run_in_thread(sleep_time=0.01, daemon=True)

    def publish(self, run_id: str, event: dict[str, Any]) -> None:
        self._mirror(run_id, event)
        self._r.publish(self.CHANNEL + run_id, json.dumps(event, default=str))

    def close(self, run_id: str) -> None:
        # Broadcast so every worker streaming this run ends its SSE loop.
        self._r.publish(self.CHANNEL + run_id, json.dumps({"type": "_close"}))

    def _on_message(self, message: dict) -> None:
        channel = message.get("channel", "")
        if isinstance(channel, bytes):
            channel = channel.decode()
        run_id = channel[len(self.CHANNEL):]
        data = message.get("data", "")
        if isinstance(data, bytes):
            data = data.decode()
        try:
            event = json.loads(data)
        except (ValueError, TypeError):
            return
        self._deliver_local(run_id, event)
        if event.get("type") == "_close":
            self._drop(run_id)


def _make_bus() -> EventBus:
    url = (os.environ.get("REDIS_URL") or "").strip()
    if not url:
        return EventBus()
    try:
        import redis
    except ImportError:
        log.warning("REDIS_URL set but redis-py missing; events stay in-process")
        return EventBus()
    try:
        client = redis.from_url(url, decode_responses=True)
        client.ping()
    except redis.exceptions.RedisError as exc:
        log.warning("Redis events unreachable (%s); events stay in-process", exc)
        return EventBus()
    log.info("Redis event bus active — multi-worker SSE enabled")
    return RedisEventBus(client)


BUS = _make_bus()


def sse_format(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"
