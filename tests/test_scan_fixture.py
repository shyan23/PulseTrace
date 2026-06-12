import json
from pathlib import Path

from lib.relevance import Term, weighted_relevance

_FIXTURE = Path("data/runs/1781288869-8922e8/posts.json")

# Hand-built plan mirroring what parse_query yields for the failing topic.
_PLAN = [
    Term("budget", 0.6, False, ["budget", "cheap", "affordable", "value"]),
    Term("headphone", 0.9, False,
         ["headphone", "headphones", "headset", "earbud", "earbuds", "cans"]),
    Term("2026", 0.05, False, ["2026"]),
]

_JUNK = ("AITA", "MTG", "long hairs", "PS Plus", "PS5", "cardboard")
_REL_FLOOR = 0.45


def _posts():
    return json.loads(_FIXTURE.read_text())


def test_no_offtopic_junk_survives_gate():
    survivors = [p for p in _posts()
                 if weighted_relevance(_PLAN, p["text"]) >= _REL_FLOOR]
    leaked = [p["text"][:60] for p in survivors
              if any(k in p["text"] for k in _JUNK)]
    assert leaked == [], f"junk leaked: {leaked}"


def test_real_headphone_posts_survive():
    survivors = [p["text"] for p in _posts()
                 if weighted_relevance(_PLAN, p["text"]) >= _REL_FLOOR]
    joined = " ".join(survivors).lower()
    assert "soundcore" in joined
    assert any("headphone" in t.lower() for t in survivors)
