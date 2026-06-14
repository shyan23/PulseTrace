from unittest.mock import patch, MagicMock
from lib.connectors.polymarket import PolymarketConnector


def _resp(payload):
    r = MagicMock()
    r.json.return_value = payload
    r.raise_for_status = lambda: None
    return r


def test_polymarket_parses_active_event():
    payload = {"events": [{
        "id": "42", "title": "Will X happen?", "slug": "will-x",
        "active": True, "closed": False, "volume1mo": "1234.5",
        "updatedAt": "2026-06-01T00:00:00Z",
        "markets": [{"question": "Will X happen by July?", "active": True, "closed": False}],
    }]}
    with patch("lib.connectors.polymarket.requests.get", return_value=_resp(payload)):
        posts = PolymarketConnector().fetch("X", limit=5)
    assert len(posts) == 1
    p = posts[0]
    assert p.source == "polymarket" and p.reactions == 1234
    assert "Will X happen?" in p.text and "by July" in p.text
    assert p.url == "https://polymarket.com/event/will-x"


def test_polymarket_skips_closed():
    payload = {"events": [
        {"id": "1", "title": "Done", "closed": True, "markets": []},
        {"id": "2", "title": "Inactive", "active": False, "markets": []},
    ]}
    with patch("lib.connectors.polymarket.requests.get", return_value=_resp(payload)):
        assert PolymarketConnector().fetch("x") == []


def test_polymarket_network_error_returns_empty():
    import requests
    with patch("lib.connectors.polymarket.requests.get",
               side_effect=requests.RequestException("boom")):
        assert PolymarketConnector().fetch("x") == []


def test_polymarket_surfaces_odds_as_percentages_in_text():
    payload = {"events": [{
        "id": "9", "title": "Brazil vs Morocco", "slug": "bra-mar",
        "active": True, "closed": False,
        "markets": [{
            "question": "Will Brazil win?", "active": True, "closed": False,
            "outcomes": "[\"Yes\", \"No\"]", "outcomePrices": "[\"0.58\", \"0.42\"]",
        }],
    }]}
    with patch("lib.connectors.polymarket.requests.get", return_value=_resp(payload)):
        post = PolymarketConnector().fetch("brazil", limit=5)[0]
    assert "Will Brazil win?" in post.text
    assert "Yes 58%" in post.text and "No 42%" in post.text


def test_polymarket_stashes_structured_odds_in_raw():
    payload = {"events": [{
        "id": "9", "title": "Brazil vs Morocco", "slug": "bra-mar",
        "active": True, "closed": False,
        "markets": [{
            "question": "Will Brazil win?", "active": True, "closed": False,
            "outcomes": "[\"Yes\", \"No\"]", "outcomePrices": "[\"0.58\", \"0.42\"]",
        }],
    }]}
    with patch("lib.connectors.polymarket.requests.get", return_value=_resp(payload)):
        post = PolymarketConnector().fetch("brazil", limit=5)[0]
    odds = post.raw["odds"]
    assert odds == [{
        "question": "Will Brazil win?",
        "outcomes": [{"name": "Yes", "prob": 0.58}, {"name": "No", "prob": 0.42}],
    }]


def test_polymarket_tolerates_malformed_prices():
    payload = {"events": [{
        "id": "9", "title": "Brazil vs Morocco", "slug": "bra-mar",
        "active": True, "closed": False,
        "markets": [{
            "question": "Will Brazil win?", "active": True, "closed": False,
            "outcomes": "[\"Yes\", \"No\"]", "outcomePrices": "not-json",
        }],
    }]}
    with patch("lib.connectors.polymarket.requests.get", return_value=_resp(payload)):
        post = PolymarketConnector().fetch("brazil", limit=5)[0]
    assert "Will Brazil win?" in post.text
    assert post.raw.get("odds") == []
