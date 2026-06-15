import pytest

import lib.embedcache as ec

fakeredis = pytest.importorskip("fakeredis")


@pytest.fixture(autouse=True)
def _isolate_singleton():
    ec.reset_embed_cache()
    yield
    ec.reset_embed_cache()


def _fake_client():
    return fakeredis.FakeStrictRedis(decode_responses=True)


def test_roundtrip_returns_stored_vectors():
    cache = ec.RedisEmbedCache(_fake_client())
    cache.put_many([("a" * 40, [1.0, 2.0, 3.0]), ("b" * 40, [4.0, 5.0])])
    got = cache.get_many(["a" * 40, "b" * 40])
    assert got["a" * 40] == [1.0, 2.0, 3.0]
    assert got["b" * 40] == [4.0, 5.0]


def test_get_many_omits_absent_keys():
    cache = ec.RedisEmbedCache(_fake_client())
    cache.put_many([("a" * 40, [1.0])])
    got = cache.get_many(["a" * 40, "missing" * 5])
    assert set(got) == {"a" * 40}


def test_empty_inputs_are_noops():
    cache = ec.RedisEmbedCache(_fake_client())
    assert cache.get_many([]) == {}
    cache.put_many([])  # must not raise


def test_ttl_sets_expiry(monkeypatch):
    client = _fake_client()
    cache = ec.RedisEmbedCache(client, ttl_seconds=3600)
    cache.put_many([("a" * 40, [1.0])])
    assert client.ttl(ec.RedisEmbedCache.PREFIX + "a" * 40) > 0


def test_factory_disabled_without_url(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    ec.reset_embed_cache()
    assert ec.get_embed_cache() is None


def test_factory_disabled_when_unreachable(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6399/0")

    class Boom:
        def ping(self):
            raise ec.redis.exceptions.ConnectionError("refused")

    monkeypatch.setattr(ec.redis, "from_url", lambda *a, **k: Boom())
    ec.reset_embed_cache()
    assert ec.get_embed_cache() is None  # never crashes the run


def test_factory_returns_cache_when_reachable(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setattr(ec.redis, "from_url", lambda *a, **k: _fake_client())
    ec.reset_embed_cache()
    cache = ec.get_embed_cache()
    assert isinstance(cache, ec.RedisEmbedCache)
    cache.put_many([("c" * 40, [9.0])])
    assert ec.get_embed_cache().get_many(["c" * 40])["c" * 40] == [9.0]
