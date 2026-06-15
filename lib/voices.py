"""Curate raw posts into opinion 'captures' for the voices / notable section.

Top-by-engagement posts are often not opinions at all — product listings, sale
ads, plot summaries, boilerplate book blurbs — yet they keyword-match the topic
and rank high. A single LLM pass keeps only genuine opinions/reactions and
rewrites each into a concise neutral capture; the original post stays one click
away. Failure is non-fatal: we fall back to the unfiltered candidates.
"""
from __future__ import annotations

from .llm import chat_json

_MAX_TEXT = 400

_SYS = (
    "You filter and condense social-media reactions for a sentiment report. "
    "You are given a topic/question and numbered reactions. Decide which are "
    "genuine opinions, reactions, or expressed sentiment ABOUT the topic. "
    "DROP anything that is not an opinion: product or sale listings, prices, "
    "advertisements, plot summaries, book/product descriptions, tables of "
    "contents, metadata, navigation text, or near-duplicates of another item. "
    "For each reaction you KEEP, write a concise neutral paraphrase (max 18 "
    "words) capturing the opinion or stance expressed — not a summary of the "
    "subject. Respond with strict JSON: "
    '{"items":[{"i":<index>,"keep":true|false,"capture":"<paraphrase or empty>"}]}. '
    "Include every index exactly once."
)


def _clip(text: str) -> str:
    t = " ".join(str(text or "").split())
    return t[:_MAX_TEXT]


def curate(topic: str, candidates: list[dict], *, max_items: int = 12) -> list[dict]:
    cands = list(candidates or [])[:max_items]
    if not cands:
        return []

    numbered = "\n".join(f"[{i}] {_clip(c.get('text', ''))}" for i, c in enumerate(cands))
    user = f'Topic / question: "{topic}"\n\nReactions:\n{numbered}'

    try:
        out = chat_json(_SYS, user, max_tokens=900, stage="voices")
    except Exception:
        return list(candidates or [])

    items = out.get("items") if isinstance(out, dict) else None
    if not isinstance(items, list):
        return list(candidates or [])

    decision: dict[int, dict] = {}
    for it in items:
        if isinstance(it, dict) and isinstance(it.get("i"), int) and 0 <= it["i"] < len(cands):
            decision[it["i"]] = it

    kept: list[dict] = []
    for i, c in enumerate(cands):
        it = decision.get(i)
        if it is None or not it.get("keep", False):
            continue
        nc = dict(c)
        cap = (it.get("capture") or "").strip()
        if cap:
            nc["capture"] = cap
        kept.append(nc)
    return kept
