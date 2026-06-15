# Agent-Engineering Stages → PulseTrace Opportunity Map

> Date: 2026-06-15
> Branch context: `feat/improved_scan`
> Method: Continuous-discovery brainstorm (PM / Designer / Engineer trio) against the
> 12-stage AI-agent engineering curriculum, grounded in the **actual** PulseTrace v2
> codebase (not the docs).
> Source skill: `pm-product-discovery:brainstorm-ideas-existing`

## Objective

Treat the 12-stage agent-engineering curriculum as a capability ladder, then map each
stage to (a) what PulseTrace already ships, (b) the gap, and (c) a concrete, fundable
feature/opportunity. PulseTrace v2 is an agentic multi-source sentiment-intelligence
platform: topic in → agent loops over multi-source fetch → embed → cluster → label →
stance → coverage-converge → topic graph, sentiment timeline, cited RAG Q&A.

This doc is the discovery artifact. Each prioritized idea links to an opportunity in the
solution tree below and carries assumptions to validate before build.

---

## Stage → Capability Map (current state vs. opportunity)

| # | Stage | Ships today | Gap | Opportunity (feature) |
|---|-------|-------------|-----|-----------------------|
| 1 | Python + Async Foundations | Flask + SSE, threaded `EventBus`, Redis pub/sub fan-out (`lib/events.py`) | Connectors fetch serially; Flask is sync; one slow source stalls the run | **Async fan-out ingestion** — connector calls become `asyncio.gather`; slow source can't block the loop. (`O1`) |
| 2 | LLM Fundamentals (routing, token econ, latency) | `lib/keypool.py`, `backend.py` selector, `compress.py` (−41.6% tokens), BYOK | Routing is static per-backend; no cost/latency-aware model choice per task | **Task-aware model router** — cheap model for label, strong for synthesis; live token-cost meter. (`O2`) |
| 3 | Tool Calling + Structured Outputs | `lib/llm.py:chat_json` strict+retry, MCP 14 tools, pydantic in `ingest/schemas.py` | Tool list is hardcoded; outputs validated ad-hoc, not via shared pydantic contracts | **Pydantic-typed tool contracts + dynamic tool discovery** for the MCP surface. (`O3`) |
| 4 | Memory + State | `chat_memory.py` rolling summary, `embedcache.py`, `store.py`, Supabase dual-write | No cross-session *user* memory; recall is per-run, not per-analyst | **Cross-session analyst memory** — "you tracked this topic last week, here's the delta." (`O4`) |
| 5 | Single-Agent Workflows (ReAct, reflect, limits) | `lib/agent.py` loop, relevance convergence + iteration cap, KMeans fallback | No explicit self-reflection step; degradation is implicit | **Self-critique node** — agent rates its own coverage/confidence and decides to expand or stop. (`O5`) |
| 6 | Multi-Agent Orchestration (LangGraph) | `lib/orchestration/{graph,nodes,runner,state}.py` on langgraph≥1.0 | Single linear graph; no supervisor, no per-source specialist agents | **Supervisor + source-specialist agents** with stance-conflict resolution. (`O6`) |
| 7 | Human-in-the-Loop | BYOK gate, manual run trigger | No uncertainty-triggered approval; no decision audit trail | **Uncertainty gate + audit trail** — low-confidence clusters pause for analyst sign-off; every agent decision logged. (`O7`) |
| 8 | Evaluation + QA | 62 test files, mocked-LLM suite | No quality eval for label/stance/RAG output; no hallucination metric | **LLM-as-judge eval harness** — score label fit, stance accuracy, citation-groundedness; regression gate in CI. (`O8`) |
| 9 | Observability + Tracing | Per-run event logs (`data/event_logs`) | No distributed tracing, no cost/latency dashboard (no langsmith/otel in deps) | **Agent trace + cost dashboard** — span per node, $/run, p95 latency, alerting. (`O9`) |
| 10 | Security + Guardrails | Supabase auth, RLS, per-user isolation | **Scraped post text is untrusted input fed to the LLM** — no prompt-injection defense, no PII redaction | **Untrusted-content guardrail** — injection screen on scraped text + PII redaction before embed/LLM. (`O10`) |
| 11 | Production Deployment | Prod at pulsetrace.publicvm.com (nginx, HTTPS, OAuth, Docker) | No self-hosted inference, no canary/rollback for agent logic | **Self-host inference + canary agent releases** (vLLM/SGLang; shadow-run new agent graph). (`O11`) |
| 12 | Open Source + Portfolio | MCP server (14 tools), in-app docs | MCP server not published; no public architecture write-up/demo | **Publish the MCP server + architecture docs + demo reel.** (`O12`) |

---

## Multi-Perspective Ideation

### Product Manager (business value, strategic alignment, customer impact)

1. **Trust Ledger** (S7+S9+S10) — every claim in a report links to its source post, the
   agent decision that surfaced it, and a confidence score. Sells the "can I trust this
   number?" objection that blocks enterprise adoption.
2. **Cost-per-Insight meter** (S2+S9) — show analysts $/run live; lets BYOK customers
   self-govern spend. Direct lever on the BYOK value prop already in the deck.
3. **Topic Watch / cross-session delta** (S4) — subscribe to a topic, get the *change*
   since last run. Converts one-shot usage into retention (current 73% → higher).
4. **Eval-gated quality SLA** (S8) — publish a measured label/stance accuracy number;
   turn QA into a marketing claim competitors can't match without the harness.
5. **Injection-safe ingestion as a compliance feature** (S10) — "we never let scraped
   content hijack the model" is a real differentiator for regulated buyers.

### Product Designer (UX, usability, delight)

1. **Agent timeline view** (S5+S9) — render the ReAct loop as a live, inspectable trace
   in the dashboard: queries tried, clusters found, why it expanded/stopped.
2. **Confidence-aware UI** (S7+S8) — low-confidence clusters get a visible "needs review"
   state with one-click analyst confirm/reject (feeds the audit trail).
3. **Source-specialist avatars** (S6) — when multi-agent lands, each source agent has a
   readable status line ("Reddit agent: 3 subs, 412 posts, done"), demystifying the loop.
4. **Spend dial** (S2) — a budget slider that visibly trades depth (more queries/sources)
   against cost before a run starts.
5. **Delta digest card** (S4) — Topic Watch result framed as a "what changed" card, not a
   full re-run dump.

### Software Engineer (technical leverage, data, scalability)

1. **Async connector fan-out** (S1) — `asyncio.gather` over connectors; per-source timeout
   so the slowest source never stalls convergence. Cheapest high-leverage win.
2. **Typed tool registry** (S3) — one pydantic contract per MCP tool; auto-generate the
   schema and validate I/O, killing ad-hoc JSON parsing.
3. **OTel spans around every graph node** (S9) — emit to the existing event bus + an OTLP
   exporter; near-free given `orchestration/` is already node-structured.
4. **LLM-judge eval harness** (S8) — replay stored runs, score label/stance/RAG with a
   judge model, fail CI on regression. Reuses `lib/replay.py`.
5. **Injection/PII filter in the ingest path** (S10) — a `lib/ingest/sanitize.py` pass
   between scrape and embed; pattern + LLM-classifier hybrid.

---

## Top 5 Prioritized

Ranked by strategic alignment × outcome impact × feasibility × differentiation, biased
toward the highest-leverage gaps (tracing, eval, guardrails) that the codebase does *not*
yet cover.

### 1. Untrusted-Content Guardrail (`O10`, Stage 10)
**One-liner:** Sanitize scraped post text for prompt injection and PII before it ever
reaches embeddings or the LLM.
**Why selected:** This is a live security hole, not a nice-to-have — PulseTrace feeds
attacker-controlled social text straight into the agent. Highest risk-adjusted value, and
it doubles as a compliance selling point.
**Assumptions to validate:**
- Injection attempts exist at non-trivial rate in real scraped corpora (sample `data/runs/`).
- A cheap classifier/pattern pass catches the bulk without nuking legitimate posts (false-positive rate acceptable).
- Redaction doesn't degrade cluster/stance quality (A/B on a stored run).

### 2. Agent Trace + Cost Dashboard (`O9`, Stages 9 + 2)
**One-liner:** A span per orchestration node streamed to the event bus, surfaced as a live
trace with $/run and p95 latency.
**Why selected:** Biggest pure gap (no tracing in deps), unblocks debugging, cost-control,
and the "Cost-per-Insight" PM play. `orchestration/` is already node-structured so the lift is small.
**Assumptions to validate:**
- OTel spans can ride the existing `EventBus`/Redis path without reworking it.
- Per-call token+cost is recoverable from `keypool`/`llm.py` today.
- Analysts actually want the trace surfaced (vs. just engineers) — test with the timeline mockup.

### 3. LLM-as-Judge Eval Harness (`O8`, Stage 8)
**One-liner:** Replay stored runs, score label fit / stance accuracy / citation-groundedness
with a judge model, and gate CI on regression.
**Why selected:** Converts "73% retention, good vibes" into a *measured* quality number —
both a regression safety net and a marketable SLA. Reuses `lib/replay.py`.
**Assumptions to validate:**
- A judge model agrees with human spot-checks enough to trust (sample agreement ≥ target).
- Stored runs are replayable deterministically enough to diff.
- Judge cost per eval run is acceptable for CI cadence.

### 4. Async Fan-out Ingestion (`O1`, Stage 1)
**One-liner:** Connectors fetch concurrently with per-source timeouts so a slow/fragile
source (Facebook) can't stall the agent loop.
**Why selected:** Cheapest high-leverage engineering win; directly improves run latency
(already chased to ~14s) and resilience, which every other stage builds on.
**Assumptions to validate:**
- Connectors are I/O-bound enough that async gives real wall-clock gain (not CPU-bound embed).
- No shared mutable state breaks under concurrency.
- Playwright FB path can be wrapped without a rewrite.

### 5. Uncertainty Gate + Audit Trail (`O7`, Stage 7)
**One-liner:** Low-confidence clusters pause for analyst confirm/reject, and every agent
decision is logged to a resumable audit trail.
**Why selected:** Turns the agent from a black box into an auditable assistant — the core
of the "Trust Ledger" enterprise story, and a natural consumer of the eval-confidence
signal from idea #3.
**Assumptions to validate:**
- A usable confidence signal exists per cluster (entropy + stance margin) to threshold on.
- Analysts will engage with review prompts rather than ignore them (test friction).
- Resume-after-approval fits the current run/store lifecycle without a state-machine rewrite.

---

## Opportunity Solution Tree (condensed)

```
OUTCOME: PulseTrace becomes a trustworthy, production-grade agentic intelligence platform
├─ O10 Untrusted-content safety ........ [TOP 1] guardrail: injection screen + PII redact
├─ O9  Can't see/cost the agent ........ [TOP 2] traces + cost dashboard
├─ O8  Can't prove output quality ...... [TOP 3] LLM-judge eval harness + CI gate
├─ O1  Slow/fragile ingestion .......... [TOP 4] async fan-out + per-source timeout
├─ O7  Agent is a black box ............ [TOP 5] uncertainty gate + audit trail
├─ O2  Spend is uncontrolled ........... task-aware model router + spend dial
├─ O4  One-shot usage, low retention ... cross-session topic watch / delta
├─ O6  Single linear graph ............. supervisor + source-specialist agents
├─ O3  Ad-hoc tool I/O ................. pydantic tool contracts + dynamic discovery
├─ O5  Implicit stop logic ............. self-critique node
├─ O11 No safe rollout ................. self-host inference + canary agent releases
└─ O12 Not externally visible .......... publish MCP server + arch docs + demo
```

## Suggested sequencing

1. **O1 async fan-out** first — foundation, unblocks latency budget for everything else.
2. **O9 tracing** next — you can't improve what you can't see; also enables O2/O8 cost data.
3. **O10 guardrail** in parallel — security debt, independent of the above.
4. **O8 eval harness** — needs stable runs from 1–3 to score against.
5. **O7 HITL gate** — consumes O8 confidence signals.

Each becomes its own spec + plan under `.claude/specs` / `.claude/plans` when picked up.
```
