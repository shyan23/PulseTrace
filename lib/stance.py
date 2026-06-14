"""Per-cluster sentiment aggregation via batched LLM."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from .compress import dedup_by, dedup_texts, expand, text_hash
from .llm import chat_json


SYS = (
    "Classify each post's sentiment toward the cluster theme. "
    'Output JSON: {"items": [{"i": <index>, "s": "pos"|"neu"|"neg"}]}'
)


def score_batch(theme: str, texts: list[str]) -> list[str]:
    if not texts:
        return []
    # Dedup copypasta/astroturf: score each distinct post once, then re-expand
    # by multiplicity. Token cost drops with the duplication rate; the
    # multiplicity-weighted tally is identical to scoring every post.
    d = dedup_texts(texts)
    enum = "\n".join(f"[{i}] {t[:400]}" for i, t in enumerate(d.uniques))
    try:
        out = chat_json(SYS, f"Theme: {theme}\nPosts:\n{enum}", max_tokens=600, stage="stance")
    except Exception:
        return ["neu"] * len(texts)
    items = out.get("items", [])
    if not isinstance(items, list):
        return ["neu"] * len(texts)
    by_i: dict[int, str] = {}
    for it in items:
        if not isinstance(it, dict):
            continue
        try:
            by_i[int(it.get("i", -1))] = str(it.get("s", "neu"))
        except (TypeError, ValueError):
            continue
    uniq_labels = [by_i.get(i, "neu") for i in range(len(d.uniques))]
    return expand(uniq_labels, d.index_of)


SYS_MIXED = (
    "Each post carries its own theme. Classify every post's sentiment toward its theme. "
    'Output JSON: {"items": [{"i": <index>, "s": "pos"|"neu"|"neg"}]}'
)


def score_mixed(items: list[tuple[str, str]]) -> list[str]:
    """Score (theme, text) pairs spanning multiple clusters in one LLM call."""
    if not items:
        return []
    # Dedup on (theme, text): the same copypasta under one theme collapses to a
    # single scored row, re-expanded by multiplicity. Distinct theme => distinct
    # row, so cross-cluster sentiment stays correct.
    d = dedup_by(items, lambda p: text_hash(p[0] + "\x00" + p[1]))
    enum = "\n".join(
        f"[{i}] (re: {theme}) {text[:400]}" for i, (theme, text) in enumerate(d.uniques)
    )
    try:
        out = chat_json(SYS_MIXED, enum, max_tokens=900, stage="stance")
    except Exception:
        return ["neu"] * len(items)
    rows = out.get("items", [])
    if not isinstance(rows, list):
        return ["neu"] * len(items)
    by_i: dict[int, str] = {}
    for it in rows:
        if not isinstance(it, dict):
            continue
        try:
            by_i[int(it.get("i", -1))] = str(it.get("s", "neu"))
        except (TypeError, ValueError):
            continue
    uniq_labels = [by_i.get(i, "neu") for i in range(len(d.uniques))]
    return expand(uniq_labels, d.index_of)


def tally(labels: list[str]) -> dict:
    if not labels:
        return {"pos": 0.0, "neu": 1.0, "neg": 0.0}
    pos = sum(1 for s in labels if s == "pos")
    neg = sum(1 for s in labels if s == "neg")
    neu = len(labels) - pos - neg
    total = max(pos + neu + neg, 1)
    return {"pos": pos / total, "neu": neu / total, "neg": neg / total}


_tally = tally  # back-compat alias


def cluster_stance_labels(themed: dict[int, tuple[str, list[str]]],
                          batch: int = 24, max_workers: int = 8) -> dict[int, list[str]]:
    """Per-post stance labels, batched across clusters in shared LLM calls.

    `themed` maps cluster id -> (theme_label, member_texts). Returns cluster id
    -> list of "pos"/"neu"/"neg" aligned 1:1 with that cluster's member_texts,
    so callers can persist which individual posts are positive/negative.
    """
    flat: list[tuple[int, str, str]] = []
    for cid, (theme, texts) in themed.items():
        for t in texts:
            flat.append((cid, theme, t))

    by_cid: dict[int, list[str]] = {cid: [] for cid in themed}
    if flat:
        chunks = [flat[s:s + batch] for s in range(0, len(flat), batch)]
        with ThreadPoolExecutor(max_workers=min(max_workers, len(chunks))) as ex:
            results = list(ex.map(lambda ch: score_mixed([(th, tx) for _, th, tx in ch]), chunks))
        for chunk, labels in zip(chunks, results):
            for (cid, _theme, _text), s in zip(chunk, labels):
                by_cid[cid].append(s)
    return by_cid


def cluster_sentiments(themed: dict[int, tuple[str, list[str]]],
                       batch: int = 24, max_workers: int = 8) -> dict:
    """Batched per-cluster sentiment fractions. Same inputs as
    `cluster_stance_labels`; returns cluster id -> {pos, neu, neg}."""
    by_cid = cluster_stance_labels(themed, batch=batch, max_workers=max_workers)
    return {cid: tally(by_cid.get(cid, [])) for cid in themed}


def cluster_sentiment(theme: str, texts: list[str], batch: int = 8) -> dict:
    pos = neu = neg = 0
    for start in range(0, len(texts), batch):
        for s in score_batch(theme, texts[start:start + batch]):
            if s == "pos":
                pos += 1
            elif s == "neg":
                neg += 1
            else:
                neu += 1
    total = max(pos + neu + neg, 1)
    return {"pos": pos / total, "neu": neu / total, "neg": neg / total}
