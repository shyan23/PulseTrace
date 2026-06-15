from __future__ import annotations

import re

from lib.obsidian import build_vault, _mood, _slug


RUN = {
    "id": "run-123",
    "topic": "Game of Thrones",
    "sources": ["reddit", "hn"],
    "finished_at": "2026-06-15T12:00:00Z",
    "metrics": {"posts": 100, "clusters": 2},
}

# Two clusters with near-identical centroids -> cosine ~1 -> an edge.
CLUSTERS = [
    {"id": 0, "label": "Season 8 Criticisms", "desc": "People hated the ending.",
     "centroid": [1.0, 0.0], "members": [1, 2, 3], "top_posts": [1],
     "sentiment": {"pos": 0.1, "neu": 0.2, "neg": 0.7}},
    {"id": 1, "label": "Season 8 Criticisms", "desc": "Rushed writing.",
     "centroid": [0.9999, 0.0141], "members": [4, 5], "top_posts": [4],
     "sentiment": {"pos": 0.8, "neu": 0.1, "neg": 0.1}},
]
POSTS = [
    {"id": 1, "source": "reddit", "text": "Worst ending ever.", "reactions": 50},
    {"id": 4, "source": "hn", "text": "The writing fell apart.", "reactions": 7},
]
EVIDENCE = {"claims": [
    {"text": "The finale was rushed and disappointing.", "side": "pro",
     "confidence": 0.82, "evidence_strength": "strong",
     "reasoning": "Many posts cite plot holes.", "cluster_ids": [0],
     "cluster_label": "Season 8 Criticisms"},
]}


def test_mood_thresholds():
    assert _mood({"pos": 0.7, "neu": 0.2, "neg": 0.1}) == "positive"
    assert _mood({"pos": 0.1, "neu": 0.2, "neg": 0.7}) == "negative"
    assert _mood({"pos": 0.45, "neu": 0.1, "neg": 0.45}) == "mixed"


def test_emits_expected_files():
    v = build_vault(RUN, CLUSTERS, POSTS, EVIDENCE)
    assert "_index.md" in v
    cluster_files = [k for k in v if k.startswith("clusters/")]
    claim_files = [k for k in v if k.startswith("claims/")]
    assert len(cluster_files) == 2
    assert len(claim_files) == 1


def test_slug_collision_appends_id():
    v = build_vault(RUN, CLUSTERS, POSTS, EVIDENCE)
    cluster_files = sorted(k for k in v if k.startswith("clusters/"))
    # Same label on both clusters must not collide.
    assert len(set(cluster_files)) == 2


def test_cluster_frontmatter_present():
    v = build_vault(RUN, CLUSTERS, POSTS, EVIDENCE)
    note = next(v[k] for k in v if k.startswith("clusters/"))
    assert note.startswith("---\n")
    assert "type: talking-point" in note
    assert "run: run-123" in note
    assert "posts: 3" in note or "posts: 2" in note
    assert re.search(r"sentiment_neg: 0\.7", note) or "sentiment_neg:" in note


def test_edge_becomes_wikilink():
    v = build_vault(RUN, CLUSTERS, POSTS, EVIDENCE)
    notes = [v[k] for k in v if k.startswith("clusters/")]
    # High-similarity pair -> each cluster links the other under Related.
    assert any("Related talking points" in n and "[[" in n for n in notes)


def test_no_edge_when_dissimilar():
    clusters = [
        {**CLUSTERS[0], "centroid": [1.0, 0.0]},
        {**CLUSTERS[1], "id": 1, "label": "Unrelated", "centroid": [0.0, 1.0]},
    ]
    v = build_vault(RUN, clusters, POSTS, None)
    for k in v:
        if k.startswith("clusters/"):
            assert "[[" not in v[k].split("Representative")[0].split("Related")[-1] \
                or "Related talking points" not in v[k]


def test_representative_posts_quoted():
    v = build_vault(RUN, CLUSTERS, POSTS, EVIDENCE)
    joined = "".join(v[k] for k in v if k.startswith("clusters/"))
    assert "Worst ending ever." in joined
    assert "reddit" in joined


def test_claim_note_links_cluster():
    v = build_vault(RUN, CLUSTERS, POSTS, EVIDENCE)
    claim = next(v[k] for k in v if k.startswith("claims/"))
    assert "type: claim" in claim
    assert "side: pro" in claim
    assert "[[" in claim  # Backs: link to its cluster


def test_empty_evidence_no_claims_no_error():
    v = build_vault(RUN, CLUSTERS, POSTS, None)
    assert not any(k.startswith("claims/") for k in v)
    assert "## Claims" not in v["_index.md"]


def test_no_dead_wikilinks():
    v = build_vault(RUN, CLUSTERS, POSTS, EVIDENCE)
    basenames = {k.rsplit("/", 1)[-1][:-3] for k in v}  # strip dir + .md
    for content in v.values():
        for target in re.findall(r"\[\[([^\]|]+)", content):
            assert target in basenames, f"dead link: {target}"


def test_slug_basic():
    assert _slug("Season 8 Criticisms!") == "season-8-criticisms"
    assert _slug("") == "note"
