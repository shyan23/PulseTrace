import time

import pytest

from lib.events import RedisEventBus

fakeredis = pytest.importorskip("fakeredis")


def _client():
    # A shared server so two bus instances see each other, like two workers.
    return fakeredis.FakeStrictRedis(server=_client.server, decode_responses=True)


_client.server = fakeredis.FakeServer()


def _drain(q, timeout=2.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not q.empty():
            return q.get_nowait()
        time.sleep(0.01)
    raise AssertionError("no event delivered in time")


def test_redis_bus_delivers_across_instances():
    publisher = RedisEventBus(_client())
    reader = RedisEventBus(_client())          # stands in for a second worker
    q = reader.subscribe("r1")
    publisher.publish("r1", {"type": "hi"})
    assert _drain(q) == {"type": "hi"}


def test_redis_bus_isolates_runs():
    publisher = RedisEventBus(_client())
    reader = RedisEventBus(_client())
    q1 = reader.subscribe("r1")
    publisher.publish("r2", {"type": "x"})
    time.sleep(0.2)
    assert q1.empty()


def test_redis_bus_close_broadcasts():
    publisher = RedisEventBus(_client())
    reader = RedisEventBus(_client())
    q = reader.subscribe("r1")
    publisher.close("r1")
    assert _drain(q) == {"type": "_close"}
