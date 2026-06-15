from __future__ import annotations

import time

from lib.agent import _run_fanout


def _slow(value, delay):
    def fn(*_a):
        time.sleep(delay)
        return [value]
    return fn


def test_runs_concurrently_not_serially():
    calls = [(_slow("a", 0.3), ()), (_slow("b", 0.3), ()), (_slow("c", 0.3), ())]
    t0 = time.time()
    out = _run_fanout(calls, timeout=5)
    elapsed = time.time() - t0
    assert out == [["a"], ["b"], ["c"]]
    assert elapsed < 0.8, f"serial would be ~0.9s, got {elapsed:.2f}s"


def test_slow_source_times_out_without_blocking():
    calls = [
        (_slow("fast", 0.05), ()),
        (_slow("stuck", 3.0), ()),     # exceeds timeout -> abandoned
        (_slow("fast2", 0.05), ()),
    ]
    t0 = time.time()
    out = _run_fanout(calls, timeout=0.4)
    elapsed = time.time() - t0
    assert out[0] == ["fast"]
    assert out[1] == []               # timed-out source yields nothing
    assert out[2] == ["fast2"]
    assert elapsed < 1.0, f"slow source blocked the loop: {elapsed:.2f}s"


def test_exception_isolated_per_source():
    def boom(*_a):
        raise RuntimeError("source down")
    calls = [(_slow("ok", 0.05), ()), (boom, ()), (_slow("ok2", 0.05), ())]
    out = _run_fanout(calls, timeout=2)
    assert out == [["ok"], [], ["ok2"]]


def test_empty_calls():
    assert _run_fanout([], timeout=1) == []


def test_preserves_order_with_mixed_delays():
    calls = [(_slow("first", 0.3), ()), (_slow("second", 0.05), ())]
    out = _run_fanout(calls, timeout=2)
    assert out == [["first"], ["second"]]   # input order, not completion order
