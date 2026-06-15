"""Export a run as an Obsidian-ready markdown vault.

Pure builder: run data -> {relpath: markdown}. Clusters become notes, similarity
edges become [[wikilinks]] (so Obsidian's graph view mirrors the topic graph),
evidence claims become notes that link back to the clusters they cite, and an
`_index.md` MOC ties it together. The server zips the dict for download.
"""
from __future__ import annotations

import math
import re
from typing import Any

EDGE_MIN = 0.5  # same similarity threshold as the /graph endpoint
_MOOD_MARGIN = 0.05


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return s or "note"


def _mood(sent: dict[str, float]) -> str:
    pos, neg = float(sent.get("pos", 0)), float(sent.get("neg", 0))
    if pos > neg + _MOOD_MARGIN:
        return "positive"
    if neg > pos + _MOOD_MARGIN:
        return "negative"
    return "mixed"


def _pct(x: float) -> int:
    return round(float(x) * 100)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _edges(clusters: list[dict]) -> list[tuple[int, int, float]]:
    out: list[tuple[int, int, float]] = []
    for i, a in enumerate(clusters):
        for b in clusters[i + 1:]:
            sim = _cosine(a.get("centroid") or [], b.get("centroid") or [])
            if sim > EDGE_MIN:
                out.append((a["id"], b["id"], sim))
    return out


def _yaml_list(items: list[str]) -> str:
    return "[" + ", ".join(items) + "]"


def _fm(pairs: list[tuple[str, Any]]) -> str:
    lines = ["---"]
    for k, v in pairs:
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _unique_slug(base: str, used: set[str], suffix: Any) -> str:
    slug = base
    if slug in used:
        slug = f"{base}-{suffix}"
    used.add(slug)
    return slug


def _cluster_note(c: dict, run: dict, slug_by_id: dict[int, str],
                  edges: list[tuple[int, int, float]], posts_by_id: dict) -> str:
    sent = c.get("sentiment") or {}
    n = len(c.get("members") or [])
    fm = _fm([
        ("type", "talking-point"),
        ("run", run.get("id", "")),
        ("topic", f'"{run.get("topic", "")}"'),
        ("posts", n),
        ("sentiment_pos", round(float(sent.get("pos", 0)), 3)),
        ("sentiment_neu", round(float(sent.get("neu", 0)), 3)),
        ("sentiment_neg", round(float(sent.get("neg", 0)), 3)),
        ("mood", _mood(sent)),
        ("created", run.get("finished_at", "")),
        ("tags", _yaml_list(["pulsetrace", "talking-point"])),
    ])
    body = [fm, f"# {c.get('label', 'Untitled')}\n"]
    if c.get("desc"):
        body.append(c["desc"] + "\n")
    body.append(
        f"**Mood:** {_pct(sent.get('pos', 0))}% positive · "
        f"{_pct(sent.get('neu', 0))}% neutral · "
        f"{_pct(sent.get('neg', 0))}% negative · {n} posts\n"
    )

    related = []
    for a, b, sim in edges:
        other = b if a == c["id"] else (a if b == c["id"] else None)
        if other is not None and other in slug_by_id:
            related.append(f"- [[{slug_by_id[other]}]] ({_pct(sim)}% similar)")
    if related:
        body.append("## Related talking points\n" + "\n".join(related) + "\n")

    reps = []
    for pid in (c.get("top_posts") or [])[:5]:
        p = posts_by_id.get(pid) or posts_by_id.get(str(pid))
        if not p:
            continue
        text = (p.get("text") or "").replace("\n", " ").strip()
        meta = p.get("source", "")
        if p.get("reactions"):
            meta += f", {p['reactions']}👍"
        reps.append(f'- "{text}" — {meta}')
    if reps:
        body.append("## Representative posts\n" + "\n".join(reps) + "\n")

    return "\n".join(body)


def _claim_note(claim: dict, run: dict, slug_by_id: dict[int, str]) -> str:
    fm = _fm([
        ("type", "claim"),
        ("run", run.get("id", "")),
        ("side", claim.get("side", "")),
        ("confidence", round(float(claim.get("confidence", 0)), 3)),
        ("evidence_strength", claim.get("evidence_strength", "")),
        ("cluster", f'"{claim.get("cluster_label", "")}"'),
        ("tags", _yaml_list(["pulsetrace", "claim", claim.get("side", "")])),
    ])
    body = [fm, f"# {claim.get('text', '')}\n",
            f"**Side:** {claim.get('side', '')} · "
            f"**Confidence:** {_pct(claim.get('confidence', 0))}% · "
            f"**Evidence:** {claim.get('evidence_strength', '')}\n"]
    if claim.get("reasoning"):
        body.append("> " + claim["reasoning"].replace("\n", " ") + "\n")
    backs = [f"[[{slug_by_id[cid]}]]" for cid in (claim.get("cluster_ids") or [])
             if cid in slug_by_id]
    if backs:
        body.append("Backs: " + ", ".join(backs) + "\n")
    return "\n".join(body)


def _index_note(run: dict, clusters: list[dict], slug_by_id: dict[int, str],
                claim_slugs: list[tuple[str, dict]]) -> str:
    m = run.get("metrics") or {}
    fm = _fm([
        ("type", "pulsetrace-run"),
        ("run", run.get("id", "")),
        ("topic", f'"{run.get("topic", "")}"'),
        ("posts", m.get("posts", 0)),
        ("clusters", m.get("clusters", len(clusters))),
        ("sources", _yaml_list(run.get("sources") or [])),
        ("created", run.get("finished_at", "")),
        ("tags", _yaml_list(["pulsetrace", "moc"])),
    ])
    body = [fm, f"# {run.get('topic', 'Run')}\n",
            f"Run `{run.get('id', '')}` · {m.get('posts', 0)} posts · "
            f"{len(clusters)} talking points · {run.get('finished_at', '')}\n"]
    tp = []
    for c in clusters:
        n = len(c.get("members") or [])
        tp.append(f"- [[{slug_by_id[c['id']]}]] — {n} posts, {_mood(c.get('sentiment') or {})}")
    if tp:
        body.append("## Talking points\n" + "\n".join(tp) + "\n")
    if claim_slugs:
        cl = [f"- [[{slug}]] — {cl.get('side', '')}, {_pct(cl.get('confidence', 0))}%"
              for slug, cl in claim_slugs]
        body.append("## Claims\n" + "\n".join(cl) + "\n")
    return "\n".join(body)


def build_vault(run: dict, clusters: list[dict], posts: list[dict],
                evidence: dict | None) -> dict[str, str]:
    posts_by_id = {p.get("id"): p for p in (posts or [])}
    edges = _edges(clusters or [])

    used: set[str] = set()
    slug_by_id: dict[int, str] = {}
    for c in clusters or []:
        slug_by_id[c["id"]] = _unique_slug(_slug(c.get("label", "")), used, c["id"])

    vault: dict[str, str] = {}
    for c in clusters or []:
        vault[f"clusters/{slug_by_id[c['id']]}.md"] = _cluster_note(
            c, run, slug_by_id, edges, posts_by_id)

    claim_slugs: list[tuple[str, dict]] = []
    for i, claim in enumerate((evidence or {}).get("claims") or []):
        slug = _unique_slug(_slug(claim.get("text", "")[:60]), used, f"c{i}")
        vault[f"claims/{slug}.md"] = _claim_note(claim, run, slug_by_id)
        claim_slugs.append((slug, claim))

    vault["_index.md"] = _index_note(run, clusters or [], slug_by_id, claim_slugs)
    return vault
