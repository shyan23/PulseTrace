#!/usr/bin/env python3
"""Frozen-corpus eval: scrape each topic once, cache it, then rerank + judge N
times on the *same* posts. This strips out scrape variance (different posts each
run) and isolates ranking + judge stability, so the mean ± std reflects the
ranker, not which posts reddit happened to surface that minute.

Mirrors the production ranking path exactly: rank_posts -> shortlist(30) ->
llm_rerank -> top-K, the same chain agent.run_agent writes to ranked.json.

Usage:
    .venv/bin/python eval/frozen_eval.py --runs 5
    .venv/bin/python eval/frozen_eval.py --runs 5 --refresh   # re-scrape corpus

Writes /tmp/frozen_eval.json and prints mean ± std vs the frozen l30d baseline.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import fields
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()
from lib import keys  # noqa: E402

keys.load()

from lib.agent import run_agent, RERANK_SHORTLIST  # noqa: E402
from lib import store  # noqa: E402
from lib.connectors.base import Post  # noqa: E402
from lib.rerank import rank_posts, llm_rerank  # noqa: E402
from eval.compare_agents import (  # noqa: E402
    judge_pool, precision_at_k, ndcg_at_k, mean_grade, n_sources,
    _load_baseline, K, SOURCES_PT, DEFAULT_TOPICS,
)

FROZEN_DIR = ROOT / "eval" / "frozen"
QUALITY_KEYS = ("n_results", "n_sources", "mean_grade", "precision_at_5", "ndcg_at_5")
_FIELDS = {f.name for f in fields(Post)}


def _post_from(d: dict) -> Post:
    return Post(**{k: v for k, v in d.items() if k in _FIELDS})


def _slug(topic: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in topic)[:50]


def corpus(topic: str, refresh: bool) -> list[Post]:
    FROZEN_DIR.mkdir(parents=True, exist_ok=True)
    cache = FROZEN_DIR / f"{_slug(topic)}.json"
    if cache.exists() and not refresh:
        return [_post_from(d) for d in json.loads(cache.read_text())]
    run_id = store.new_run_id()
    run_agent(topic, SOURCES_PT, run_id=run_id)
    posts = store.read_json(run_id, "posts.json") or []
    cache.write_text(json.dumps(posts, indent=2))
    return [_post_from(d) for d in posts]


def one_pass(topic: str, posts: list[Post]) -> dict:
    shortlist = rank_posts(topic, posts, n=RERANK_SHORTLIST)
    ranked = llm_rerank(topic, shortlist, n=K)
    items = [{"url": p.url or "", "text": p.text or "", "source": p.source or ""}
             for p in ranked]
    grades = judge_pool(topic, items)
    pool = list(grades.values())
    return {
        "n_results": len(items),
        "n_sources": n_sources(items),
        "mean_grade": round(mean_grade(items, grades), 3),
        "precision_at_5": round(precision_at_k(items, grades), 3),
        "ndcg_at_5": round(ndcg_at_k(items, grades, pool), 3),
    }


def _stats(vals: list[float]) -> tuple[float, float]:
    if not vals:
        return 0.0, 0.0
    mu = statistics.fmean(vals)
    sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    return round(mu, 3), round(sd, 3)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--topics", nargs="*", default=DEFAULT_TOPICS)
    ap.add_argument("--refresh", action="store_true", help="re-scrape frozen corpus")
    ap.add_argument("--out", default="/tmp/frozen_eval.json")
    args = ap.parse_args()

    baseline = _load_baseline().get("aggregate", {}).get("last30days_baseline", {})

    per_run_aggs: list[dict] = []
    for i in range(args.runs):
        print(f"\n===== RUN {i + 1}/{args.runs} =====", flush=True)
        rows = []
        for topic in args.topics:
            posts = corpus(topic, refresh=(args.refresh and i == 0))
            m = one_pass(topic, posts)
            rows.append(m)
            print(f"  {topic[:40]:<40} nDCG={m['ndcg_at_5']} P@5={m['precision_at_5']} "
                  f"mg={m['mean_grade']}", flush=True)
        agg = {k: round(statistics.fmean(r[k] for r in rows), 3) for k in QUALITY_KEYS}
        per_run_aggs.append(agg)

    summary = {k: _stats([a[k] for a in per_run_aggs]) for k in QUALITY_KEYS}
    out = {"runs": args.runs, "per_run": per_run_aggs,
           "summary_mean_std": {k: {"mean": v[0], "std": v[1]} for k, v in summary.items()},
           "l30d_baseline": baseline}
    Path(args.out).write_text(json.dumps(out, indent=2))

    print(f"\n===== FROZEN-CORPUS RESULT  (N={args.runs} reranks on same posts) =====")
    print(f"{'metric':<16}{'PT mean':>10}{'± std':>9}{'l30d':>9}{'verdict':>9}")
    for k in QUALITY_KEYS:
        mu, sd = summary[k]
        b = baseline.get(k)
        if b is None:
            verdict = "-"
        elif mu - sd > b:
            verdict = "WIN"
        elif mu + sd < b:
            verdict = "lose"
        else:
            verdict = "tie"
        bs = f"{b}" if b is not None else "-"
        print(f"{k:<16}{mu:>10}{sd:>9}{bs:>9}{verdict:>9}")
    print(f"\nWIN = mean-std still above l30d (non-overlapping). Raw -> {args.out}")


if __name__ == "__main__":
    main()
