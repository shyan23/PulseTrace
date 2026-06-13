"""Token-saving representative selection + dedup for LLM batches.

Adapted from headroom's `anchor_selector` / SmartCrusher ideas, ported to
PulseTrace's free-text social-post records:

- `information_score` — rank near-duplicate records by rare-value + length +
  structural uniqueness so a small sample preserves signal *diversity*, not
  just position (faithful port of headroom's dict scorer).
- dedup-by-hash — collapse identical / near-identical texts (copypasta,
  astroturf), score each distinct text once, then re-expand by multiplicity.
  Token savings scale with the duplication rate; the multiplicity-weighted
  tally is unchanged, so sentiment proportions stay exact.
- `pick_representatives` — choose the most informative distinct subset under a
  budget instead of naive first-N truncation, with pattern/recency-aware
  positional anchors.

Pure logic, stdlib only. No network, no LLM — safe to unit-test in isolation.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Callable, Sequence, TypeVar

T = TypeVar("T")

_WS = re.compile(r"\s+")
_URL = re.compile(r"https?://\S+")
_PUNCT = re.compile(r"[^\w\s]")

# Query keywords that bias positional anchoring toward one end of the array.
_RECENCY_KW = ("latest", "recent", "newest", "now", "today", "current", "breaking")
_HISTORICAL_KW = ("history", "historical", "origin", "earliest", "first", "past", "background")


# ─── Normalization + dedup key ────────────────────────────────────────────


def normalize_text(s: str) -> str:
    """Lowercase, drop URLs + punctuation, collapse whitespace.

    The normalized form is the dedup key: it folds together copypasta that
    differs only in trailing links, casing, or punctuation.
    """
    s = _URL.sub("", s or "").lower()
    s = _PUNCT.sub(" ", s)
    return _WS.sub(" ", s).strip()


def text_hash(s: str) -> str:
    """Stable 16-char dedup hash of a text's normalized form."""
    return hashlib.md5(normalize_text(s).encode()).hexdigest()[:16]  # nosec B324


# ─── Dedup + reweight ─────────────────────────────────────────────────────


@dataclass
class DedupResult:
    """Outcome of collapsing a sequence onto distinct representatives.

    - `uniques`:  first-seen representative per distinct group, in order.
    - `counts`:   multiplicity of each unique (sums to original length).
    - `index_of`: original-position -> unique-index, for re-expansion.
    """

    uniques: list[Any]
    counts: list[int]
    index_of: list[int]

    @property
    def saved(self) -> int:
        """How many items the dedup removed from the LLM payload."""
        return len(self.index_of) - len(self.uniques)


def dedup_by(items: Sequence[T], key: Callable[[T], str]) -> DedupResult:
    """Collapse `items` onto distinct groups keyed by `key(item)`."""
    seen: dict[str, int] = {}
    uniques: list[Any] = []
    counts: list[int] = []
    index_of: list[int] = []
    for it in items:
        h = key(it)
        u = seen.get(h)
        if u is None:
            u = len(uniques)
            seen[h] = u
            uniques.append(it)
            counts.append(1)
        else:
            counts[u] += 1
        index_of.append(u)
    return DedupResult(uniques, counts, index_of)


def dedup_texts(texts: Sequence[str]) -> DedupResult:
    """Collapse texts that share a normalized form (near-duplicate fold)."""
    return dedup_by(texts, text_hash)


def expand(per_unique: Sequence[T], index_of: Sequence[int]) -> list[T]:
    """Map a per-unique result back to the original order and length."""
    return [per_unique[u] for u in index_of]


# ─── Information score (faithful dict port) ───────────────────────────────


def information_score(item: dict[str, Any], all_items: Sequence[dict[str, Any]]) -> float:
    """Information-density score for a record vs its corpus, in [0, 1].

    Blend of three signals (headroom weights: 0.4 / 0.3 / 0.3):
      1. value uniqueness   — rare field values score higher
      2. content length     — longer records carry more
      3. structural rarity  — unusual field sets (errors, edge cases)
    """
    if not item or not all_items or not isinstance(item, dict):
        return 0.0
    score = (
        _value_uniqueness(item, all_items) * 0.4
        + _length_score(item, all_items) * 0.3
        + _structural_uniqueness(item, all_items) * 0.3
    )
    return min(1.0, max(0.0, score))


def _val_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, sort_keys=True)
    except (TypeError, ValueError):
        return str(value)


def _value_uniqueness(item: dict[str, Any], all_items: Sequence[dict[str, Any]]) -> float:
    if len(all_items) < 2:
        return 0.5
    counts: dict[str, Counter[str]] = {}
    for other in all_items:
        if not isinstance(other, dict):
            continue
        for k, v in other.items():
            counts.setdefault(k, Counter())[_val_str(v)] += 1
    total = len(all_items)
    rareness = [
        1.0 - counts[k].get(_val_str(v), 0) / total
        for k, v in item.items()
        if k in counts and counts[k].get(_val_str(v), 0) > 0
    ]
    return sum(rareness) / len(rareness) if rareness else 0.5


def _length_score(item: dict[str, Any], all_items: Sequence[dict[str, Any]]) -> float:
    if len(all_items) < 2:
        return 0.5
    lens = [len(_val_str(i)) for i in all_items if isinstance(i, dict)]
    if not lens:
        return 0.5
    lo, hi = min(lens), max(lens)
    if hi == lo:
        return 0.5
    return (len(_val_str(item)) - lo) / (hi - lo)


def _structural_uniqueness(item: dict[str, Any], all_items: Sequence[dict[str, Any]]) -> float:
    valid = [i for i in all_items if isinstance(i, dict)]
    n = len(valid)
    if n < 2:
        return 0.5
    field_counts: Counter[str] = Counter()
    for other in valid:
        field_counts.update(other.keys())
    common = {k for k, v in field_counts.items() if v >= n * 0.8}
    rare = {k for k, v in field_counts.items() if v < n * 0.2}
    fields = set(item.keys())
    uniqueness = 0.0
    if rare:
        uniqueness += 0.5 * (len(fields & rare) / max(len(rare), 1))
    if common:
        uniqueness += 0.5 * (len(common - fields) / max(len(common), 1))
    return min(1.0, uniqueness)


# ─── Text information score (IDF-based, for free-text posts) ───────────────


def text_information_scores(texts: Sequence[str]) -> list[float]:
    """Per-text density score in [0, 1]: rare-token mass + relative length.

    The dict scorer needs uniform records; social posts are free text, so we
    use mean inverse-document-frequency (rare wording scores higher) blended
    with normalized length. A distinct rant outscores the Nth identical
    "this!!!" reply.
    """
    docs = [normalize_text(t).split() for t in texts]
    n = len(docs)
    if n == 0:
        return []
    df: Counter[str] = Counter()
    for d in docs:
        df.update(set(d))
    max_len = max((len(d) for d in docs), default=1) or 1
    log_n = math.log(n) if n > 1 else 1.0
    out: list[float] = []
    for d in docs:
        if not d:
            out.append(0.0)
            continue
        uniq = set(d)
        idf = sum(math.log(n / df[w]) for w in uniq) / len(uniq)
        idf_norm = (idf / log_n) if n > 1 else 0.0
        out.append(min(1.0, 0.7 * idf_norm + 0.3 * (len(d) / max_len)))
    return out


# ─── Representative selection (anchor + density) ──────────────────────────


def _anchor_slots(k: int, query: str | None) -> tuple[int, int]:
    """Reserved (front, back) positional slots, shifted by query intent."""
    front, back = 1, 1
    q = (query or "").lower()
    if any(w in q for w in _RECENCY_KW) and not any(w in q for w in _HISTORICAL_KW):
        back = 2
    elif any(w in q for w in _HISTORICAL_KW) and not any(w in q for w in _RECENCY_KW):
        front = 2
    front = min(front, k)
    back = min(back, max(0, k - front))
    return front, back


def pick_representatives(texts: Sequence[str], k: int, *, query: str | None = None) -> list[str]:
    """Choose <=k distinct, maximally-informative texts (original order).

    Replaces naive `texts[:k]`: dedups first so the budget spends on distinct
    content, keeps front/back positional anchors (recency/historical-aware),
    then fills the remaining slots by information score.
    """
    if k <= 0:
        return []
    uniques = dedup_texts(texts).uniques
    n = len(uniques)
    if n <= k:
        return list(uniques)
    scores = text_information_scores(uniques)
    front, back = _anchor_slots(k, query)
    chosen: set[int] = set(range(front)) | {n - 1 - i for i in range(back)}
    remaining = k - len(chosen)
    if remaining > 0:
        mid = sorted(
            (i for i in range(n) if i not in chosen),
            key=lambda i: scores[i],
            reverse=True,
        )[:remaining]
        chosen.update(mid)
    return [uniques[i] for i in sorted(chosen)]
