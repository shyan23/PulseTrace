from unittest.mock import patch, MagicMock
from lib.connectors.google import GoogleConnector


def _resp(payload):
    r = MagicMock()
    r.json.return_value = payload
    r.raise_for_status = lambda: None
    return r


_PAYLOAD = {"code": 200, "status": 20000, "data": [
    {"title": "Brazil vs Morocco preview",
     "url": "https://example.com/a",
     "description": "Tactical breakdown of the World Cup clash",
     "content": "Brazil enter as favourites...", "date": "2026-06-10"},
    {"title": "Morocco squad named",
     "url": "https://example.com/b",
     "description": "Regragui picks his XI", "content": ""},
]}


def test_google_parses_jina_results():
    with patch.dict("os.environ", {"JINA_API": "jina_test"}), \
         patch("lib.connectors.google.requests.get", return_value=_resp(_PAYLOAD)):
        posts = GoogleConnector().fetch("Brazil vs Morocco", limit=5)
    assert len(posts) == 2
    p = posts[0]
    assert p.source == "google"
    assert p.url == "https://example.com/a"
    assert "Brazil vs Morocco preview" in p.text
    assert "Tactical breakdown" in p.text


def test_google_sends_bearer_key():
    captured = {}

    def fake_get(url, **kw):
        captured["headers"] = kw.get("headers", {})
        return _resp(_PAYLOAD)

    with patch.dict("os.environ", {"JINA_API": "jina_secret"}), \
         patch("lib.connectors.google.requests.get", side_effect=fake_get):
        GoogleConnector().fetch("x", limit=3)
    assert captured["headers"]["Authorization"] == "Bearer jina_secret"


def test_google_no_key_returns_empty():
    with patch.dict("os.environ", {"JINA_API": ""}, clear=False), \
         patch("lib.connectors.google.requests.get") as g:
        posts = GoogleConnector().fetch("x")
    assert posts == []
    g.assert_not_called()


def test_google_network_error_returns_empty():
    import requests
    with patch.dict("os.environ", {"JINA_API": "jina_test"}), \
         patch("lib.connectors.google.requests.get",
               side_effect=requests.RequestException("boom")):
        assert GoogleConnector().fetch("x") == []


def test_google_skips_empty_text_rows():
    payload = {"data": [{"title": "", "url": "https://e.com/x",
                         "description": "", "content": ""}]}
    with patch.dict("os.environ", {"JINA_API": "jina_test"}), \
         patch("lib.connectors.google.requests.get", return_value=_resp(payload)):
        assert GoogleConnector().fetch("x") == []
