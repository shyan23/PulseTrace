from __future__ import annotations
import pytest

from lib import keypool


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_BACKUP_KEY", raising=False)
    keypool.reset()
    yield
    keypool.reset()


def test_primary_only(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "primary")
    assert keypool.gemini_keys() == ["primary"]
    assert keypool.current_gemini_key() == "primary"
    assert keypool.advance_gemini_key() is False
    assert keypool.current_gemini_key() == "primary"


def test_failover_to_backup(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "primary")
    monkeypatch.setenv("GEMINI_BACKUP_KEY", "backup")
    assert keypool.current_gemini_key() == "primary"
    assert keypool.advance_gemini_key() is True
    assert keypool.current_gemini_key() == "backup"
    assert keypool.advance_gemini_key() is False


def test_multiple_backups_and_dedup(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k1")
    monkeypatch.setenv("GEMINI_BACKUP_KEY", "k2, k3 , k2")
    assert keypool.gemini_keys() == ["k1", "k2", "k3"]


def test_strips_quotes(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", '"quoted"')
    assert keypool.gemini_keys() == ["quoted"]


def test_no_keys_returns_empty_sentinel():
    assert keypool.gemini_keys() == []
    assert keypool.current_gemini_key() == "EMPTY"


@pytest.mark.parametrize("msg", [
    "Error code: 429 - RESOURCE_EXHAUSTED",
    "Your project has exceeded its monthly spending cap",
    "quota exceeded for this key",
    "rate limit reached",
])
def test_is_quota_error_true(msg):
    assert keypool.is_quota_error(Exception(msg)) is True


def test_is_quota_error_by_status_code():
    e = Exception("boom")
    e.status_code = 429
    assert keypool.is_quota_error(e) is True


def test_is_quota_error_false():
    assert keypool.is_quota_error(Exception("400 invalid api key")) is False
