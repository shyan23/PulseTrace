from unittest.mock import patch

from lib.queryparse import QueryPlan, parse_query


_LLM_OK = {
    "subject": "wireless headphone",
    "terms": [
        {"term": "wireless", "weight": 0.9, "required": True,
         "variants": ["wireless", "bluetooth", "bt"]},
        {"term": "headphone", "weight": 0.9, "required": False,
         "variants": ["headphone", "headphones", "headset"]},
        {"term": "2026", "weight": 0.05, "required": False, "variants": ["2026"]},
    ],
    "entities": ["bose", "sony"],
    "stance": "skeptical about market headphones",
}


@patch("lib.queryparse.chat_json")
def test_parse_returns_structured_plan(mock_llm):
    mock_llm.return_value = _LLM_OK
    parse_query.cache_clear()
    plan = parse_query("skeptical about wireless headphones 2026, compare bose and sony")
    assert isinstance(plan, QueryPlan)
    assert plan.subject == "wireless headphone"
    assert plan.entities == ["bose", "sony"]
    assert plan.stance


@patch("lib.queryparse.chat_json")
def test_adjective_is_required_year_is_low_weight(mock_llm):
    mock_llm.return_value = _LLM_OK
    parse_query.cache_clear()
    plan = parse_query("best wireless headphone 2026")
    by_term = {t.term: t for t in plan.terms}
    assert by_term["wireless"].required is True
    assert by_term["headphone"].required is False
    assert by_term["2026"].weight <= 0.1


@patch("lib.queryparse.chat_json")
def test_llm_failure_falls_back_to_heuristic(mock_llm):
    mock_llm.side_effect = ValueError("bad json")
    parse_query.cache_clear()
    plan = parse_query("best wireless headphone 2026")
    assert isinstance(plan, QueryPlan)
    assert plan.subject
    assert plan.terms
    assert plan.stance == ""


@patch("lib.queryparse.chat_json")
def test_runtime_error_also_falls_back(mock_llm):
    # provider-cascade exhaustion raises RuntimeError, not just bad JSON
    mock_llm.side_effect = RuntimeError("cascade exhausted")
    parse_query.cache_clear()
    plan = parse_query("best wireless headphone 2026")
    assert plan.terms
    assert plan.stance == ""


@patch("lib.queryparse.chat_json")
def test_empty_query_returns_empty_plan_without_llm(mock_llm):
    parse_query.cache_clear()
    plan = parse_query("   ")
    assert plan.subject == ""
    assert plan.terms == []
    mock_llm.assert_not_called()


@patch("lib.queryparse.chat_json")
def test_parse_is_cached(mock_llm):
    mock_llm.return_value = _LLM_OK
    parse_query.cache_clear()
    parse_query("same query text")
    parse_query("same query text")
    assert mock_llm.call_count == 1
