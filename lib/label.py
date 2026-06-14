"""LLM-named cluster labels from sample post texts."""
from __future__ import annotations
from .compress import pick_representatives
from .llm import chat_json


SYS = (
    "You name clusters of social posts. Output strict JSON: "
    '{"label": "<=6 words", "desc": "1-2 sentences"}'
)


def label_cluster(samples: list[str]) -> dict:
    if not samples:
        return {"label": "Empty", "desc": ""}
    # Pick the 8 most distinct posts instead of the first 8 near-duplicates —
    # a more diverse sample yields a sharper cluster name at the same cost.
    body = "\n\n---\n\n".join(s[:500] for s in pick_representatives(samples, 8))
    try:
        out = chat_json(SYS, f"Posts in this cluster:\n{body}", stage="label")
    except Exception:
        return {"label": "General discussion", "desc": ""}
    return {
        "label": str(out.get("label", "General discussion"))[:80],
        "desc": str(out.get("desc", ""))[:300],
    }
