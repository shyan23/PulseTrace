"""Tests for lib/compress.py — dedup/reweight + representative selection."""
from __future__ import annotations

from lib import compress as C


# ─── normalize + hash ──────────────────────────────────────────────────────


def test_normalize_folds_case_url_punctuation():
    a = C.normalize_text("Love this!!! https://x.com/abc")
    b = C.normalize_text("love this")
    assert a == b == "love this"


def test_text_hash_matches_for_near_duplicates():
    assert C.text_hash("BUY NOW!!! http://spam.io") == C.text_hash("buy now")
    assert C.text_hash("alpha") != C.text_hash("beta")


# ─── dedup + expand ─────────────────────────────────────────────────────────


def test_dedup_collapses_and_preserves_multiplicity():
    texts = ["great product", "great product!", "terrible", "great product"]
    d = C.dedup_texts(texts)
    assert d.uniques == ["great product", "terrible"]
    assert d.counts == [3, 1]
    assert sum(d.counts) == len(texts)
    assert d.saved == 2


def test_expand_restores_original_order_and_length():
    texts = ["a", "b", "a", "a"]
    d = C.dedup_texts(texts)
    # Score uniques once ("a"->pos, "b"->neg), expand back to every original.
    per_unique = ["pos", "neg"]
    assert C.expand(per_unique, d.index_of) == ["pos", "neg", "pos", "pos"]


def test_dedup_empty():
    d = C.dedup_texts([])
    assert d.uniques == [] and d.counts == [] and d.index_of == []


# ─── information_score (dict port) ──────────────────────────────────────────


def test_information_score_rewards_rare_value():
    corpus = [{"k": "x"}, {"k": "x"}, {"k": "x"}, {"k": "rare"}]
    common = C.information_score({"k": "x"}, corpus)
    rare = C.information_score({"k": "rare"}, corpus)
    assert rare > common


def test_information_score_rewards_structural_outlier():
    corpus = [{"k": "v"}, {"k": "v"}, {"k": "v"}, {"k": "v", "error": "boom"}]
    plain = C.information_score({"k": "v"}, corpus)
    outlier = C.information_score({"k": "v", "error": "boom"}, corpus)
    assert outlier > plain


def test_information_score_edge_cases():
    assert C.information_score({}, [{"a": 1}]) == 0.0
    assert C.information_score({"a": 1}, []) == 0.0


# ─── text_information_scores ────────────────────────────────────────────────


def test_text_scores_rank_distinct_above_boilerplate():
    texts = ["nice", "nice", "nice", "the regulatory framework affects quarterly margins"]
    scores = C.text_information_scores(texts)
    assert scores[3] > scores[0]


def test_text_scores_empty_and_blank():
    assert C.text_information_scores([]) == []
    assert C.text_information_scores(["", ""]) == [0.0, 0.0]


# ─── pick_representatives ───────────────────────────────────────────────────


def test_pick_dedups_before_budget():
    texts = ["dup", "dup", "dup", "dup", "unique insight here"]
    out = C.pick_representatives(texts, 8)
    assert out == ["dup", "unique insight here"]  # only 2 distinct


def test_pick_respects_budget_and_returns_distinct():
    texts = [f"distinct opinion number {i} about the topic" for i in range(20)]
    out = C.pick_representatives(texts, 5)
    assert len(out) == 5
    assert len(set(out)) == 5


def test_pick_keeps_informative_over_boilerplate():
    texts = ["ok"] * 9 + ["a detailed nuanced argument about policy tradeoffs"]
    # 10 inputs but only 2 distinct -> both kept regardless of budget.
    out = C.pick_representatives(texts, 3)
    assert "a detailed nuanced argument about policy tradeoffs" in out


def test_pick_recency_query_shifts_to_back():
    texts = [f"item {i}" for i in range(10)]
    out = C.pick_representatives(texts, 3, query="what is the latest reaction")
    # recency bias reserves two back anchors -> last item always kept
    assert "item 9" in out


def test_pick_zero_budget():
    assert C.pick_representatives(["a", "b"], 0) == []
