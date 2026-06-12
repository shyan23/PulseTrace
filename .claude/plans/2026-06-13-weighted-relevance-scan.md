# Weighted Relevance Scan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat token-overlap relevance gate with an LLM-weighted, self-attention-style model where qualifying adjectives are hard-required and search steering is balance-managed, driven by a single free-form query box.

**Architecture:** A new `lib/queryparse.py` makes one cached LLM call per run that turns a free-form query into a `QueryPlan` (subject, weighted terms, entities, stance). A pure deterministic `weighted_relevance` scorer in `lib/relevance.py` gates posts: hard-drop if any required term is absent, else soft weighted coverage. The agent loop parses once and threads the plan through seeding (balanced), gating, expansion, and the opinion page. The existing heuristic is the fallback when the LLM parse fails.

**Tech Stack:** Python 3.12, `lib/llm.py:chat_json` (strict JSON + retry), dataclasses, pytest with `unittest.mock`.

**Spec:** `.claude/specs/2026-06-13-weighted-relevance-scan-design.md`

---

## File Structure

- `lib/relevance.py` (modify) — owns the pure `Term` dataclass + `weighted_relevance` + `_variant_tokens`. No new deps (stays pure so the LLM layer can import it, not vice-versa).
- `lib/queryparse.py` (create) — owns `QueryPlan` + `parse_query` (the only LLM boundary) + deterministic fallback. Imports `Term` from `relevance`.
- `lib/agent.py` (modify) — parse once; weighted gate; tunable `REL_FLOOR`; drop `opinion` param; always-balanced seeds.
- `lib/orchestration/*` + `server.py` (modify) — drop `opinion` field; thread `QueryPlan`/`stance`.
- `templates/partials/_app.html` (modify) — single free-form input box.
- `tests/test_relevance.py` (modify), `tests/test_queryparse.py` (create), `tests/test_scan_fixture.py` (create).

---

## Task 1: `Term` dataclass + `weighted_relevance` scorer (pure)

**Files:**
- Modify: `lib/relevance.py`
- Test: `tests/test_relevance.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_relevance.py`:

```python
from lib.relevance import Term, weighted_relevance


def _plan():
    return [
        Term("wireless", 0.9, True, ["wireless", "bluetooth", "bt"]),
        Term("headphone", 0.9, False, ["headphone", "headphones", "headset", "cans"]),
        Term("2026", 0.05, False, ["2026"]),
    ]


def test_weighted_hard_drop_when_required_absent():
    # wired headphones: required "wireless" (+variants) absent -> hard drop
    assert weighted_relevance(_plan(), "best wired audiophile headphones 2026") == 0.0


def test_weighted_variant_satisfies_required():
    # "bluetooth" is a variant of required "wireless"
    s = weighted_relevance(_plan(), "Bose QC bluetooth headphones, great in 2026")
    assert s >= 0.9


def test_weighted_year_only_is_zero():
    # only the year matches, required "wireless" absent -> hard drop (the original bug)
    assert weighted_relevance(_plan(), "AITA for keeping MTG cards gifted in 2026") == 0.0


def test_weighted_soft_partial_when_noun_misses():
    # wireless present (required ok) but noun "headphone" absent -> partial soft score
    s = weighted_relevance(_plan(), "wireless bluetooth speaker review 2026")
    assert 0.0 < s < 0.9


def test_weighted_required_late_in_body_counts():
    # required term appears only at the end -> still counts
    s = weighted_relevance(_plan(), "Long review of headphones. Finally, they are wireless.")
    assert s >= 0.9


def test_weighted_empty_plan_is_neutral():
    assert weighted_relevance([], "anything") == 0.5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_relevance.py -k weighted -v`
Expected: FAIL — `ImportError: cannot import name 'Term'`.

- [ ] **Step 3: Implement `Term` + scorer**

Add to the top of `lib/relevance.py` after `import re`:

```python
from dataclasses import dataclass, field


@dataclass
class Term:
    term: str
    weight: float
    required: bool = False
    variants: list[str] = field(default_factory=list)
```

Add at the end of `lib/relevance.py`:

```python
def _variant_tokens(term: Term) -> set[str]:
    toks: set[str] = set()
    for v in [term.term, *term.variants]:
        toks |= tokenize(v)
    return toks


def weighted_relevance(terms: list[Term], text: str) -> float:
    """Hard-required gate + soft weighted coverage, in [0.0, 1.0]."""
    if not terms:
        return 0.5
    tokens = tokenize(text)
    for r in terms:
        if r.required and not (_variant_tokens(r) & tokens):
            return 0.0
    total = sum(t.weight for t in terms) or 1.0
    matched = sum(t.weight for t in terms if _variant_tokens(t) & tokens)
    return round(matched / total, 3)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_relevance.py -v`
Expected: PASS (all, including the pre-existing year/plural tests).

- [ ] **Step 5: Commit**

```bash
git add lib/relevance.py tests/test_relevance.py
git commit -m "feat(relevance): weighted scorer with hard-required terms"
```

---

## Task 2: `queryparse.py` — `QueryPlan` + `parse_query` + fallback

**Files:**
- Create: `lib/queryparse.py`
- Test: `tests/test_queryparse.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_queryparse.py`:

```python
from unittest.mock import patch

from lib.queryparse import QueryPlan, parse_query


_LLM_OK = {
    "subject": "wireless headphone",
    "terms": [
        {"term": "wireless", "weight": 0.9, "required": True,
         "variants": ["wireless", "bluetooth", "bt"]},
        {"term": "headphone", "weight": 0.9, "required": False,
         "variants": ["headphone", "headphones", "headset"]},
        {"term": "2026", "weight": 0.05, "required": False, "variants": ["2026"]},
    ],
    "entities": ["bose", "sony"],
    "stance": "skeptical about market headphones",
}


@patch("lib.queryparse.chat_json")
def test_parse_returns_structured_plan(mock_llm):
    mock_llm.return_value = _LLM_OK
    plan = parse_query("skeptical about wireless headphones 2026, compare bose and sony")
    assert isinstance(plan, QueryPlan)
    assert plan.subject == "wireless headphone"
    assert plan.entities == ["bose", "sony"]
    assert plan.stance


@patch("lib.queryparse.chat_json")
def test_adjective_is_required_year_is_low_weight(mock_llm):
    mock_llm.return_value = _LLM_OK
    plan = parse_query("best wireless headphone 2026")
    by_term = {t.term: t for t in plan.terms}
    assert by_term["wireless"].required is True
    assert by_term["headphone"].required is False
    assert by_term["2026"].weight <= 0.1


@patch("lib.queryparse.chat_json")
def test_llm_failure_falls_back_to_heuristic(mock_llm):
    mock_llm.side_effect = ValueError("bad json")
    plan = parse_query("best wireless headphone 2026")
    assert isinstance(plan, QueryPlan)
    assert plan.subject  # heuristic core subject
    assert plan.terms     # heuristic terms, never empty for non-empty query
    assert plan.stance == ""


@patch("lib.queryparse.chat_json")
def test_parse_is_cached(mock_llm):
    mock_llm.return_value = _LLM_OK
    parse_query.cache_clear()
    parse_query("same query text")
    parse_query("same query text")
    assert mock_llm.call_count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_queryparse.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'lib.queryparse'`.

- [ ] **Step 3: Implement `lib/queryparse.py`**

```python
"""Free-form query -> structured scan plan.

One LLM call (cached) turns a natural-language query into weighted terms with
hard-required qualifying adjectives, named entities to also search, and the
user's expressed stance (display only). Falls back to the deterministic
heuristic in lib/relevance when the LLM is unavailable or returns bad JSON.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from .llm import chat_json
from .relevance import (
    Term,
    extract_core_subject,
    tokenize,
    _is_generic_token,
    _singularize,
)


@dataclass
class QueryPlan:
    subject: str
    terms: list[Term]
    entities: list[str] = field(default_factory=list)
    stance: str = ""


_SYSTEM = (
    "You are a query analyst for a social-media research agent. Read the user's "
    "free-form query and return a strict JSON plan. Assign each meaningful term a "
    "weight in [0,1] by how essential it is to the subject. A qualifying ADJECTIVE "
    "(wireless, budget, noise-cancelling) is REQUIRED (required=true). The head NOUN "
    "is high-weight but required=false. A bare year or number (2026) or generic word "
    "(best, latest, review) gets weight <= 0.1 and required=false. For each term give "
    "morphological + synonym variants (wireless -> [wireless, bluetooth, bt]). Extract "
    "named entities to also search (brands/products) and the user's stance/opinion "
    "(for display only, never used to bias search)."
)
_SCHEMA_HINT = (
    'Output JSON: {"subject": "...", "terms": [{"term": "...", "weight": 0.0-1.0, '
    '"required": true|false, "variants": ["..."]}], "entities": ["..."], "stance": "..."}'
)


def _heuristic_plan(raw: str) -> QueryPlan:
    subject = extract_core_subject(raw) or raw
    terms: list[Term] = []
    for tok in tokenize(subject):
        weight = 0.05 if _is_generic_token(tok) else 1.0
        variants = [tok]
        sing = _singularize(tok)
        if sing:
            variants.append(sing)
        terms.append(Term(tok, weight, required=False, variants=variants))
    return QueryPlan(subject=subject, terms=terms, entities=[], stance="")


@lru_cache(maxsize=256)
def parse_query(raw: str) -> QueryPlan:
    raw = (raw or "").strip()
    if not raw:
        return QueryPlan(subject="", terms=[], entities=[], stance="")
    try:
        data = chat_json(_SYSTEM, f"{raw}\n\n{_SCHEMA_HINT}", max_tokens=600)
        terms = [
            Term(
                term=str(t["term"]),
                weight=float(t.get("weight", 0.5)),
                required=bool(t.get("required", False)),
                variants=[str(v) for v in t.get("variants", [])],
            )
            for t in data.get("terms", [])
            if t.get("term")
        ]
        if not terms:
            return _heuristic_plan(raw)
        return QueryPlan(
            subject=str(data.get("subject") or extract_core_subject(raw) or raw),
            terms=terms,
            entities=[str(e) for e in data.get("entities", [])],
            stance=str(data.get("stance") or ""),
        )
    except (ValueError, KeyError, TypeError):
        return _heuristic_plan(raw)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_queryparse.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add lib/queryparse.py tests/test_queryparse.py
git commit -m "feat(queryparse): free-form query -> weighted QueryPlan with fallback"
```

---

## Task 3: Agent integration — weighted gate, balanced seeds, drop `opinion`

**Files:**
- Modify: `lib/agent.py` (signature `:148`, seeds `:161`, gate `:209-217`, expand `:307`, constants `:32-35`, `_llm_seed` `:61`, `_llm_next` `:75`, evidence `:378`)
- Test: `tests/test_agent_math.py` (verify untouched), manual run check

- [ ] **Step 1: Make `REL_FLOOR` tunable and raise it**

In `lib/agent.py` change the constants block:

```python
REL_FLOOR = 0.30          # weighted relevance below this = noise (was 0.12 token gate)
RERANK_SHORTLIST = 30
MIN_ONTOPIC = 6           # keep all posts if fewer survive the gate (recall guard)
EXPAND_REL_FLOOR = 0.30   # drop expansion queries that drift off the core subject
```

- [ ] **Step 2: Update imports + always-balanced seeds**

Change the import line:

```python
from .relevance import weighted_relevance, extract_core_subject
from .queryparse import parse_query, QueryPlan
```

Replace `_SEED_NEUTRAL`/`_SEED_OPINION` selection. Set the seed system prompt to always seek balance, and drop the `opinion` arg:

```python
_SEED_BALANCED = (
    "You generate social-media search queries for a research agent. Given a subject "
    "and optional named entities, output queries that DELIBERATELY cover three stances "
    "so the result set is balanced: positive/praise, negative/complaints, and neutral/"
    "comparison. Keep every query about the subject's core; do not invent opinions. "
    'Output JSON: {"queries": ["..."]}'
)


def _llm_seed(subject: str, entities: list[str]) -> list[str]:
    user = f"Subject: {subject}"
    if entities:
        user += f"\nAlso cover entities: {', '.join(entities)}"
    try:
        data = chat_json(_SEED_BALANCED, user, max_tokens=300)
        qs = [str(q) for q in data.get("queries", []) if q][:6]
        return qs or [subject]
    except (ValueError, KeyError, TypeError):
        return [subject]
```

- [ ] **Step 3: Update `_llm_next` to drop `opinion`**

```python
def _llm_next(topic: str, labels: list[str]) -> dict:
    user = (
        f"Topic: {topic}\nClusters so far: {labels}\n"
        "Decide stop or expand; if expand, propose up to 3 new queries on under-covered "
        'angles. Output JSON: {"action": "stop"|"expand", "queries": ["..."]}'
    )
    try:
        return chat_json(_SEED_BALANCED.split("Output")[0], user, max_tokens=300)
    except (ValueError, KeyError, TypeError):
        return {"action": "stop", "queries": []}
```

(Keep whatever `_llm_next` system prompt already exists if richer; the required change is only removing the `opinion` parameter and its branches at `:75-79`.)

- [ ] **Step 4: Update `run_agent` signature + parse once + weighted gate**

Change signature at `:148`:

```python
def run_agent(topic: str, sources: list[str], run_id: str | None = None,
              close_bus: bool = True) -> str:
```

After `run_id` is set and before seeding, parse once:

```python
    plan = parse_query(topic)
    core = plan.subject or extract_core_subject(topic) or topic
```

Replace the seed call at `:161`:

```python
    seeds = _llm_seed(plan.subject or core, plan.entities)
```

Replace the gate at `:209-210`:

```python
        on_topic = [p for p in posts
                    if weighted_relevance(plan.terms, p.text) >= REL_FLOOR]
```

Replace the expand call at `:307`:

```python
        decision = _llm_next(topic, [c["label"] for c in cluster_meta])
```

Replace the evidence call at `:378`:

```python
        build_evidence(run_id, plan.stance or None)
```

- [ ] **Step 5: Run agent math + relevance + queryparse tests**

Run: `.venv/bin/python -m pytest tests/test_agent_math.py tests/test_relevance.py tests/test_queryparse.py -v`
Expected: PASS (math untouched; relevance + queryparse green).

- [ ] **Step 6: Commit**

```bash
git add lib/agent.py
git commit -m "feat(agent): weighted gate, balanced seeds, single free-form query"
```

---

## Task 4: Update callers — `server.py` and orchestration graph

**Files:**
- Modify: `server.py:371,379,397,420`
- Modify: `lib/orchestration/state.py` and the graph entry that accepts `opinion` (grep `opinion`)

- [ ] **Step 1: Find every remaining `opinion=` caller**

Run: `grep -rn "opinion" server.py lib/orchestration/ lib/dispatch.py lib/replay.py lib/mcp/ --include=*.py | grep -v stance`
Record each hit — every one must be updated or removed.

- [ ] **Step 2: Update `/run` and graph endpoints in `server.py`**

Remove the opinion extraction and pass-through. At `:371` and `:397` delete the
`opinion = (data.get("opinion") or "").strip() or None` lines. At `:379`:

```python
            run_agent(topic, sources, run_id=run_id)
```

At `:420` (graph path) drop the `opinion=opinion` kwarg:

```python
            run_graph_streamed(topic, sources, run_id)
```

- [ ] **Step 3: Update the orchestration graph signature**

In `run_graph_streamed` (and any `GraphState`/node that carries `opinion`), remove the
`opinion` parameter/field. Where the graph builds seeds or evidence, mirror Task 3: call
`parse_query(topic)` once, store the resulting `QueryPlan` on the state, and use
`plan.terms` for any relevance gating and `plan.stance` for evidence.

- [ ] **Step 4: Run the full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: PASS. Fix any test still passing `opinion=` to `run_agent`/graph by removing it.

- [ ] **Step 5: Commit**

```bash
git add server.py lib/orchestration/
git commit -m "refactor: drop opinion steering param across entry paths"
```

---

## Task 5: Single free-form input box

**Files:**
- Modify: `templates/partials/_app.html` (the topic + opinion form)

- [ ] **Step 1: Collapse the two inputs into one textarea**

Find the topic input and the separate opinion input in `templates/partials/_app.html`.
Remove the opinion field. Replace the topic input with a single textarea whose value
posts as `topic`:

```html
<textarea name="topic" id="topic" rows="2"
  placeholder="e.g. skeptical about wireless headphones — what's best this year? compare Bose & Sony"
  class="query-box"></textarea>
```

Ensure the form no longer sends an `opinion` field (remove the input and any JS that reads it).

- [ ] **Step 2: Verify the form posts only `topic` + `sources`**

Run: `grep -n "opinion" templates/partials/_app.html static/js/*.js 2>/dev/null`
Expected: no remaining `opinion` references in the submit path.

- [ ] **Step 3: Commit**

```bash
git add templates/partials/_app.html static/
git commit -m "feat(ui): single free-form query box, remove opinion field"
```

---

## Task 6: Regression fixture + REL_FLOOR calibration

**Files:**
- Create: `tests/test_scan_fixture.py`
- Uses: `data/runs/1781288869-8922e8/posts.json`

- [ ] **Step 1: Write the regression test**

Create `tests/test_scan_fixture.py`:

```python
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
_REL_FLOOR = 0.30


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
```

- [ ] **Step 2: Run and calibrate**

Run: `.venv/bin/python -m pytest tests/test_scan_fixture.py -v`
Expected: PASS. If `test_real_headphone_posts_survive` fails, the head-noun weight or
`budget` variants are too strict — widen variants, NOT lower the floor below 0.30.
If junk leaks, raise `_REL_FLOOR` and update `REL_FLOOR` in `lib/agent.py` to match.

- [ ] **Step 3: Commit**

```bash
git add tests/test_scan_fixture.py
git commit -m "test(scan): regression fixture pins the year-leak fix"
```

---

## Task 7: Full-suite verification

- [ ] **Step 1: Run everything**

Run: `.venv/bin/python -m pytest -q`
Expected: all green. No reference to `opinion=` in `run_agent`/graph callers remains.

- [ ] **Step 2: Smoke-run the agent on the failing topic (mocked or live)**

If an LLM backend is configured, run a real scan for `Best Budget friendly Headphone 2026`
and confirm posts.json contains no AITA/MTG/PS5 entries. Otherwise rely on Task 6 fixture.

- [ ] **Step 3: Final commit / push prep**

```bash
git status
git log --oneline shyan..HEAD
```

---

## Self-Review

**Spec coverage:**
- §1 queryparse → Task 2. ✓
- §2 weighted_relevance → Task 1. ✓
- §3 agent gate + balanced seeds + drop opinion → Task 3. ✓
- §4 single input box → Task 5. ✓
- §5 rerank unchanged (no task needed — explicitly unchanged). ✓
- §6 REL_FLOOR → 0.30 tunable + calibration → Task 3 (constant) + Task 6 (calibration). ✓
- §7 opinion page from stance → Task 3 Step 4 (`build_evidence(plan.stance)`) + Task 4 graph. ✓
- Migration (drop `opinion=` callers) → Task 4. ✓
- Tests (queryparse, relevance, fixture) → Tasks 1, 2, 6. ✓

**Type consistency:** `Term(term, weight, required, variants)` and `QueryPlan(subject, terms, entities, stance)` used identically in Tasks 1–6. `weighted_relevance(terms, text)`, `parse_query(raw)`, `_llm_seed(subject, entities)`, `_llm_next(topic, labels)`, `build_evidence(run_id, stance|None)` consistent across tasks.

**Placeholder scan:** Task 3 Step 3 notes "keep existing richer prompt if present" — acceptable (the concrete required change, removing `opinion`, is shown). Task 4 Step 3 is the one genuinely codebase-dependent step (LangGraph state shape varies); it gives the exact pattern to mirror (parse once, store plan, use terms/stance) rather than guessed line numbers.
