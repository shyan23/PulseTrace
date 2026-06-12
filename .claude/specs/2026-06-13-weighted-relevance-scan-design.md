# Weighted Relevance Scan — Design Spec

> Branch: `feat/improved_scan`
> Date: 2026-06-13
> Supersedes the flat token-overlap gate with an LLM-weighted, self-attention-style
> relevance model. Motivated by a real bug: topic `Best Budget friendly Headphone 2026`
> surfaced off-topic AITA / MTG / PS5 posts because any post mentioning the bare year
> `2026` cleared the relevance floor.

## Problem

Two compounding defects in the current scan (`lib/relevance.py`, `lib/agent.py`):

1. **Bare year/number tokens carry topical weight.** `token_overlap_relevance` scored an
   AITA post `0.17` against `budget friendly headphone 2026` purely because both contained
   `2026`. That cleared `REL_FLOOR = 0.12`, so the pre-cluster gate kept it.
2. **User-supplied `opinion` steering biases search.** The `opinion` param fed
   `_llm_seed`, which produced one-sided Anker-only seed queries — the opinion page then
   reflected that skew rather than the platform's real mix of views.

A hotfix already landed on this branch (treat pure-digit tokens as generic; singularize
plurals; cap generic-only matches below the floor). This spec replaces that *heuristic*
with a principled, LLM-weighted model and keeps the hotfix as the deterministic fallback.

## Goals

- Relevance is decided by **per-term semantic weight**, not token presence.
- Qualifying **adjectives are hard requirements**; the head noun is soft/high-weight.
- Search **steering is balance-managed by the LLM** (pro / con / neutral coverage), not
  by a user-injected conclusion.
- One **free-form input box**: need + opinion + entities in natural language.
- The scan stays **deterministic after a single per-run LLM parse**, and fully testable.

## Non-goals

- No per-post LLM relevance judging in the gate (too costly / nondeterministic — the
  existing `llm_rerank` stays as the final *sort*).
- No embedding-similarity gate (can't enforce hard "wireless required").
- No change to clustering, stance, RAG, or storage.

---

## Architecture

```
free-form query
   │
   ▼
[1] queryparse.parse_query()  ── 1 LLM call/run (temp 0, cached) ──┐
   │   {subject, terms[{term,weight,required,variants}],          │ fallback on
   │    entities, stance}                                          │ failure ▼
   │                                                    extract_core_subject +
   ▼                                                    heuristic term weights
[2] _llm_seed(subject, entities)  → stance-balanced seed queries
   │   (pro / con / neutral angles; NO opinion bias)
   ▼
[3] fetch → dedup (unchanged)
   │
   ▼
[4] weighted_relevance(terms, post.text)  → gate at REL_FLOOR (tunable, ~0.30)
   │   hard-drop if any required term absent; else soft weighted coverage
   ▼
[5] embed → cluster → label → stance  (unchanged)
   ▼
[6] llm_rerank  → final sort (no drop)
   ▼
[7] opinion page  ← extracted stance + balanced corpus
```

---

## Components

### 1. `lib/queryparse.py` (new)

Single responsibility: turn a free-form query string into a structured scan plan.

```python
@dataclass
class Term:
    term: str
    weight: float        # 0.0–1.0, semantic importance
    required: bool       # hard filter (qualifying adjectives)
    variants: list[str]  # synonyms/morphology for matching

@dataclass
class QueryPlan:
    subject: str             # compact search subject, e.g. "wireless headphone"
    terms: list[Term]
    entities: list[str]      # named things to also search, e.g. ["bose","sony"]
    stance: str              # user's expressed opinion — DISPLAY ONLY, never seeds

def parse_query(raw: str) -> QueryPlan: ...
```

- One `chat_json` call (temperature 0) through `lib/llm.py`, `response_format=json_object`,
  one retry on parse failure (per coding standards).
- **Cached** by a hash of `raw` so re-runs of the same query are deterministic and free.
- **Classification rules** in the prompt:
  - qualifying **adjective** (wireless, budget, noise-cancelling) → `required: true`,
    high weight, with variants (`wireless → [wireless, bluetooth, bt]`).
  - **head noun** (headphone) → `required: false`, high weight, morphological variants
    (`headphone → [headphone, headphones, headset, cans]`).
  - **year / bare number / generic** (2026, best, latest) → low weight (≤0.1),
    `required: false`.
- **Fallback** (LLM error / invalid JSON after retry): build a `QueryPlan` from the
  existing heuristic — `extract_core_subject` for `subject`, each surviving token as a
  soft `Term` (weight 1.0, `required: false`), `_is_generic_token` → weight 0.05,
  `_singularize` → variants, `entities=[]`, `stance=""`. The scan never hard-fails.

### 2. `lib/relevance.py` (extend)

Add the deterministic weighted scorer; keep all existing functions as the fallback path.

```python
def weighted_relevance(terms: list[Term], text: str) -> float:
    """Hard-required gate + soft weighted coverage, in [0.0, 1.0]."""
    if not terms:
        return 0.5                           # empty plan = neutral (matches legacy)
    T = tokenize(text)                       # full body; "said after" still counts
    for r in (t for t in terms if t.required):
        if not any(v in T for v in _variant_tokens(r)):
            return 0.0                       # missing a required term → off-topic
    total = sum(t.weight for t in terms) or 1.0
    matched = sum(t.weight for t in terms
                  if any(v in T for v in _variant_tokens(t)))
    return round(matched / total, 3)
```

- `_variant_tokens(term)` = tokenized `{term.term} ∪ term.variants` (re-using `tokenize`,
  which already lowercases, strips punctuation, and singularizes).
- Required-term presence is checked over the **entire** post text (title + body), so a
  required word appearing later in a post still satisfies it.
- `token_overlap_relevance` is unchanged and used only by the fallback path / legacy callers.

### 3. `lib/agent.py` (edit)

- `run_agent` drops the `opinion: str | None` parameter. The single free-form `topic`
  is parsed once via `parse_query`; the resulting `QueryPlan` flows through the loop.
- Seed generation: `_llm_seed(plan.subject, plan.entities)` — prompt instructs the model
  to emit **stance-balanced** queries (positive, negative, neutral angles) so the corpus
  supports a fair pro/con/neutral opinion page. No opinion bias.
- Gate (`agent.py:~209`): replace
  `token_overlap_relevance(core, p.text) >= REL_FLOOR`
  with `weighted_relevance(plan.terms, p.text) >= REL_FLOOR`.
- `REL_FLOOR`: promote to a tunable module constant, **start 0.30**, calibrate against the
  fixture (below). The `MIN_ONTOPIC = 6` recall guard is retained unchanged.
- Expansion floor (`EXPAND_REL_FLOOR`): score expansion queries with the same weighted
  model so drifted expansions are dropped consistently.

### 4. Input template (edit)

Collapse the two-field (topic + opinion) form into a **single free-form textarea**. No
backend opinion field. Placeholder guides natural language
("e.g. *skeptical about wireless headphones — what's best this year? compare Bose & Sony*").
The extracted `stance` still populates the opinion page.

### 5. Rerank / opinion page

- `llm_rerank` is unchanged — **final sort only, no drop** (default). Hard-required + the
  raised floor already remove junk pre-cluster; dropping post-cluster risks recall.
- Opinion page is unchanged structurally; it now reads from a deliberately balanced corpus
  + extracted `stance`, so its pro/con/neutral split is trustworthy.

---

## Data flow / interface contract

`parse_query(raw) → QueryPlan` is the only new boundary. Everything downstream consumes
`QueryPlan` fields:

| Consumer            | Reads from QueryPlan         |
|---------------------|------------------------------|
| `_llm_seed`         | `subject`, `entities`        |
| `weighted_relevance`| `terms`                      |
| opinion page        | `stance`                     |

`QueryPlan` is the single source of truth for a run, so a unit that has it can be
understood and tested without re-reading the LLM prompt.

## Error handling

- LLM parse failure → deterministic heuristic `QueryPlan` (never hard-fail).
- Connector failures → unchanged (log + continue).
- Empty query → empty `QueryPlan` (no terms) → `weighted_relevance` returns `0.5` neutral
  (matches current empty-query behaviour), gate keeps posts (recall guard).
- All-required-terms-missing across the whole corpus → `MIN_ONTOPIC` recall guard prevents
  an empty result by keeping the unfiltered set, and a `low_recall` event is published.

## Testing (heavy — explicit project ask)

`tests/test_queryparse.py` (mocked LLM via `unittest.mock.patch` on `chat_json`):
- schema shape + dataclass parsing.
- adjective → `required: true`; head noun → `required: false`; year → weight ≤ 0.1.
- variants present for adjective + noun.
- LLM-failure → deterministic fallback plan (asserts no exception, sane terms).
- caching: same `raw` → one LLM call.

`tests/test_relevance.py` (extend; pure, no mocks):
- hard drop when a required term (and all variants) absent → `0.0`.
- soft partial when noun matches but a non-required term misses.
- variant match (`bluetooth` satisfies required `wireless`).
- year-only post → `0.0` (the original bug).
- plural post satisfies singular term.
- required term appearing late in body still counts.

`tests/test_scan_fixture.py` (new; regression on real run `1781288869-8922e8`):
- load `data/runs/1781288869-8922e8/posts.json`.
- assert **0** of {AITA, MTG, "long hairs", PS5/PS Plus, cardboard} survive the gate.
- assert Soundcore / Bose / wireless-headphone posts survive.
- use this fixture to calibrate the final `REL_FLOOR` value.

Existing `tests/test_rerank.py`, `tests/test_agent_*.py` must stay green (signature change
to `run_agent` — update callers and their tests).

## Migration / compatibility

- `run_agent(..., opinion=...)` callers (`server.py`, `lib/dispatch.py`, replay, MCP tools,
  tests) must drop the `opinion` argument. Grep `opinion=` before merge; update each.
- The hotfix already on this branch (`_is_generic_token`, `_singularize`, 0.10 cap) stays —
  it is the fallback path's scorer.

## Open / deferred

- Optional future: let `llm_rerank` hard-drop below `RELEVANT_CUT` behind a flag
  (default off). Not in this spec.
- Optional future: persist the `QueryPlan` into `run.json` for auditability.
