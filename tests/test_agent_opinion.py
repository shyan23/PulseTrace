from __future__ import annotations
from unittest.mock import patch
from lib import agent


def test_seed_balanced_prompt_covers_three_stances():
    captured = {}

    def fake(system, user, **kw):
        captured["system"] = system
        captured["user"] = user
        return {"queries": ["a", "b", "c"]}

    with patch("lib.agent.chat_json", side_effect=fake):
        qs = agent._llm_seed("Elden Ring", [])
    assert qs == ["a", "b", "c"]
    blob = captured["system"].lower()
    assert "positive" in blob or "praise" in blob
    assert "negative" in blob or "complaint" in blob
    assert "neutral" in blob or "comparison" in blob


def test_seed_includes_entities_in_user_prompt():
    captured = {}

    def fake(system, user, **kw):
        captured["user"] = user
        return {"queries": ["q1"]}

    with patch("lib.agent.chat_json", side_effect=fake):
        agent._llm_seed("headphones", ["Sony", "Bose"])
    assert "Sony" in captured["user"]
    assert "Bose" in captured["user"]


def test_seed_no_entities_omits_entity_line():
    captured = {}

    def fake(system, user, **kw):
        captured["user"] = user
        return {"queries": ["q1"]}

    with patch("lib.agent.chat_json", side_effect=fake):
        agent._llm_seed("headphones", [])
    assert "entities" not in captured["user"].lower()


def test_seed_falls_back_to_subject_on_llm_error():
    with patch("lib.agent.chat_json", side_effect=ValueError("bad json")):
        assert agent._llm_seed("Topic", []) == ["Topic"]


def test_seed_caps_at_6_queries():
    def fake(system, user, **kw):
        return {"queries": [f"q{i}" for i in range(10)]}

    with patch("lib.agent.chat_json", side_effect=fake):
        result = agent._llm_seed("Elden Ring", [])
    assert len(result) == 6


def test_next_has_no_opinion_framing():
    captured = {}

    def fake(system, user, **kw):
        captured["system"] = system
        return {"action": "stop", "queries": []}

    with patch("lib.agent.chat_json", side_effect=fake):
        agent._llm_next("Elden Ring", ["combat"])
    assert "opinion" not in captured["system"].lower()


def test_next_stop_action_returned():
    def fake(system, user, **kw):
        return {"action": "stop", "queries": []}

    with patch("lib.agent.chat_json", side_effect=fake):
        result = agent._llm_next("Elden Ring", ["combat"])
    assert result["action"] == "stop"


def test_next_expand_action_returned():
    def fake(system, user, **kw):
        return {"action": "expand", "queries": ["new query"]}

    with patch("lib.agent.chat_json", side_effect=fake):
        result = agent._llm_next("Elden Ring", ["combat"])
    assert result["action"] == "expand"
    assert "new query" in result["queries"]
