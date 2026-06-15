from __future__ import annotations

from unittest.mock import patch

from lib import voices


CANDS = [
    {"text": "Best book in the series, the Snape twist destroyed me.", "url": "u1"},
    {"text": "Selling Fiction & Non-Fiction Books @50% Off MRP. Pickup near RGA Tech Park.", "url": "u2"},
    {"text": "Harry Potter and the Half-Blood Prince: Signature Edition. Takes up the story of Harry's sixth year...", "url": "u3"},
    {"text": "Felt like filler honestly, too much teen romance, not enough plot.", "url": "u4"},
]


def _fake_decision(*_a, **_k):
    return {"items": [
        {"i": 0, "keep": True, "capture": "Loved it; the Snape twist was devastating."},
        {"i": 1, "keep": False, "capture": ""},
        {"i": 2, "keep": False, "capture": ""},
        {"i": 3, "keep": True, "capture": "Found it filler — too much romance, thin plot."},
    ]}


def test_drops_non_opinions_and_adds_capture():
    with patch.object(voices, "chat_json", _fake_decision):
        out = voices.curate("opinion on Half-Blood Prince", CANDS)
    assert len(out) == 2
    texts = [c["text"] for c in out]
    assert "Selling Fiction" not in texts[0] + texts[1]
    assert out[0]["capture"].startswith("Loved it")
    assert out[0]["url"] == "u1"  # original preserved for click-through


def test_empty_candidates():
    assert voices.curate("x", []) == []


def test_llm_failure_falls_back_unfiltered():
    def boom(*_a, **_k):
        raise RuntimeError("no key")
    with patch.object(voices, "chat_json", boom):
        out = voices.curate("x", CANDS)
    assert out == CANDS  # graceful: unfiltered, never crashes the section


def test_bad_shape_falls_back():
    with patch.object(voices, "chat_json", lambda *a, **k: {"nope": 1}):
        out = voices.curate("x", CANDS)
    assert out == CANDS


def test_keep_without_capture_keeps_post():
    def dec(*_a, **_k):
        return {"items": [{"i": 0, "keep": True}, {"i": 1, "keep": False},
                          {"i": 2, "keep": False}, {"i": 3, "keep": False}]}
    with patch.object(voices, "chat_json", dec):
        out = voices.curate("x", CANDS)
    assert len(out) == 1
    assert "capture" not in out[0]  # no paraphrase -> falls back to raw text in UI


def test_unknown_index_ignored():
    def dec(*_a, **_k):
        return {"items": [{"i": 99, "keep": True, "capture": "ghost"}]}
    with patch.object(voices, "chat_json", dec):
        out = voices.curate("x", CANDS)
    assert out == []  # nothing valid kept
