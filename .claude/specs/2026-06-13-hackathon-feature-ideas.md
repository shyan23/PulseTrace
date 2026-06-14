# PulseTrace v2 — Hackathon Feature Ideas

> Generated via `pm-product-discovery:brainstorm-ideas-existing` (Product Trio: PM / Designer / Engineer → prioritized top 5).
> Date: 2026-06-13. Author: discovery session.
> Lens: features **worthy of winning a hackathon** = solves a *real, painful* problem, is *demoable in 3 minutes*, and is *defensible* (hard for a judge's team to clone in a weekend).

---

## 0. Framing: what real problem are we actually in?

PulseTrace already does the hard plumbing: agentic multi-source crawl → embed → cluster → label → stance → coverage-convergence → cited RAG → coordination detection → briefing PDF. That's a *capability*. Hackathons don't reward capabilities; they reward **a wedge into one urgent job**.

The three urgent jobs PulseTrace is uniquely positioned for, given its existing assets:

| Asset already in repo | Unfair advantage it unlocks |
|---|---|
| `coordination.py` (astroturf detection) | Inauthenticity / influence-ops detection |
| Polymarket connector (rare!) | Sentiment-as-leading-indicator vs hard market odds |
| Topic graph + timeline + cited RAG | Narrative provenance ("where did this claim start?") |
| Multi-platform fetch + per-cluster stance | Cross-platform *framing divergence* (echo-chamber audit) |
| Orchestration alert node (`should_alert`) | Real-time early-warning, not just retrospective reports |

Everything below leans on at least one of these so it can't be cloned by a generic "ChatGPT-over-Reddit" demo.

---

## 1. Ideation — three perspectives

### 🧭 Product Manager (business value, strategic fit, customer impact)

1. **Narrative Provenance Tracing ("Patient Zero")** — for any claim/talking-point, reconstruct the earliest appearance and the cross-platform spread path with timestamps. Buyers: trust-&-safety, journalists, comms teams.
2. **Sentiment–Market Divergence Signal** — overlay PulseTrace sentiment trend against Polymarket odds; flag when crowd *mood* diverges from crowd *money* (a tradeable/forecastable signal). Buyers: analysts, traders, forecasters.
3. **Coordinated-Campaign Early-Warning** — turn the existing one-shot coordination detector into a live monitor that fires an alert the moment an inauthentic cluster forms. Buyers: brand/platform integrity teams.
4. **Reputation Risk Score (board-ready)** — a single 0–100 daily index per tracked entity with the 3 drivers, exportable to the briefing PDF. Buyers: PR/IR, execs.
5. **Stance-Shift Explainer** — when sentiment flips on a topic, auto-pin the *event* that caused it ("approval dropped 18 pts after the recall announcement"). Buyers: comms, policy, product marketing.

### 🎨 Product Designer (UX, usability, delight)

1. **Live "Narrative Map" replay** — scrub a timeline slider and watch the topic graph *grow* node-by-node, showing how a story spread (uses the SSE bus you already have).
2. **"Why this verdict?" evidence drawer** — every sentiment %, every cluster label gets a one-click drawer showing the exact cited posts that drove it (extends current cited-RAG into the dashboard itself).
3. **Confidence + freshness badges** — every number carries a "based on N posts, M sources, last updated X" chip so users trust (and distrust) appropriately.
4. **Split-screen Platform Framing view** — same topic, two columns (e.g. Reddit vs Facebook), surfacing how each community frames it differently.
5. **One-line "brief me" prompt → narrated 30-sec briefing** — type a topic, get an auto-played, captioned summary card stack (demo gold).

### ⚙️ Software Engineer (technical leverage, data, scalability)

1. **Streaming claim-graph dedup** — reuse the new `lib/compress.py` info-score + hashing to collapse near-duplicate posts into *claim nodes* (the unit of provenance), not raw posts.
2. **Cross-platform stance-divergence metric** — cheap: you already compute per-cluster stance; just group by source and compute KL/JS divergence between source-level sentiment distributions.
3. **Leading-indicator backtester** — replay historical runs (you have `replay.py`) against Polymarket resolution to measure if sentiment *led* odds. Turns a claim into a measured number.
4. **Coordination → alert webhook** — wire `coordination.py` output into the orchestration `should_alert` node + an outbound webhook/Slack. Minimal code, high demo impact.
5. **Synthetic-account fingerprinting** — extend `influence.py` with account-age/posting-cadence/text-template features to score *who* is likely inauthentic, not just *that* a cluster is.

---

## 2. Prioritized Top 5

Scored on: strategic fit · impact · feasibility-in-a-hackathon · differentiation.

### 🥇 #1 — Narrative Provenance Tracer ("Patient Zero")
**One-liner:** For any talking-point, reconstruct who said it *first* and trace its mutation/spread across platforms as an animated claim-graph.

**Why selected:** Highest "judges lean forward" factor. Misinformation provenance is a genuinely unsolved, high-stakes problem (elections, health, brand crises). You already have the graph, the timeline, the cited RAG, and now near-dup compression to build *claim nodes*. Nobody clones this in a weekend.

**Build sketch:** `compress.py` collapses posts → claim nodes; sort claim first-seen timestamps across sources; render with existing Cytoscape graph + SSE replay; cited-RAG drawer proves each edge.

**Assumptions to validate:**
- Timestamps from each connector are reliable/comparable enough to order origin (⚠️ FB OCR has no reliable timestamp — may need to scope to Reddit/HN/X/Bluesky first).
- Near-dup claim clustering is accurate enough that "first node" is meaningful, not noise.
- Users care about *origin*, not just *current* sentiment (interview to confirm).

### 🥈 #2 — Sentiment × Market Divergence Signal
**One-liner:** Overlay PulseTrace sentiment against Polymarket odds and flag when public *mood* and public *money* disagree — a forecasting edge.

**Why selected:** Uses your **rarest asset** (Polymarket connector) for something no sentiment tool does. Demoable with a concrete, falsifiable claim ("sentiment led the odds by 6 hours on event X"). Backtestable → not hand-wavy.

**Build sketch:** align sentiment timeline with odds series; compute lead/lag correlation; `replay.py` backtests against resolved markets for a credibility number.

**Assumptions to validate:**
- Topics overlap: enough social chatter exists for active Polymarket questions.
- Sentiment actually leads (not lags) odds on a meaningful fraction of events — the whole pitch dies if it lags.
- Lead/lag is stable enough to be a "signal," not a coin flip.

### 🥉 #3 — Coordinated-Campaign Early-Warning + Alert
**One-liner:** Live monitor that fires the instant an inauthentic/coordinated cluster forms, with a "who + why" inauthenticity fingerprint.

**Why selected:** Smallest gap between today and demo — `coordination.py` + the orchestration `should_alert` node already exist; this wires them into a live alert + webhook and adds account fingerprinting. High real-world demand (integrity teams), strong visual ("watch it catch a bot swarm live").

**Build sketch:** orchestration node calls `coordination.detect` per iteration → on hit, emit SSE `alert` + outbound webhook; extend `influence.py` with cadence/age/template features for per-account scores.

**Assumptions to validate:**
- Detection precision is high enough that alerts aren't crying wolf (false-positive cost is reputational).
- Connectors expose enough account metadata (age, history) to fingerprint — may be thin on FB/IG.
- A live coordinated example is reproducible for the demo (pre-seed a known case).

### #4 — Cross-Platform Framing Divergence ("Echo-Chamber Audit")
**One-liner:** Show, side by side, how the *same* topic is framed and felt differently across platforms/communities, with a single divergence score.

**Why selected:** Cheap to build (you already compute per-cluster stance — just group by source + compute distribution divergence), yet visually striking and genuinely insightful. Great "aha" moment for judges.

**Build sketch:** group stance by source; JS-divergence between source sentiment distributions; split-screen UI + top divergent claims per platform.

**Assumptions to validate:**
- Per-source post volume is balanced enough to compare (FB yielding 0 due to OCR 429 would break it — see infra risk below).
- Divergence is interpretable to users, not just a number.

### #5 — "Why this verdict?" Trust Layer (evidence + confidence everywhere)
**One-liner:** Every sentiment %, label, and score in the dashboard becomes click-through to the exact cited posts, with confidence/freshness badges.

**Why selected:** Not a flashy headline feature, but it's the difference between a toy and a *trusted* tool — and it's the cheapest credibility multiplier for all four ideas above. Judges trust demos they can interrogate.

**Build sketch:** extend cited-RAG to annotate dashboard numbers; add "N posts / M sources / updated X" chips; reuse `evidence.py`.

**Assumptions to validate:**
- Users distrust un-sourced AI numbers enough to value this (very likely true post-2024).
- Citation density is high enough that most numbers *have* a drawer to open.

---

## 3. Recommended hackathon play

**Lead with #1 (Provenance) as the headline, back it with #5 (Trust Layer) so it's believable, and keep #3 (Live Alert) as the "and it runs in real-time" closer.** That trio tells one story: *"PulseTrace doesn't just tell you the mood — it shows you where a narrative started, proves every claim, and catches manufactured ones as they happen."*

If the judges are finance/markets-flavored, swap the headline to **#2 (Market Divergence)** — it's the most "there's a business here" of the five.

---

## 4. ⚠️ Infra risk that gates all five (must fix first)

Current runs show **Facebook yielding 0 posts** — every Gemini vision-OCR call returns `429` (quota exhausted), and the agent then stops early (`agent_stop`) on a starved 12-post corpus. **Three of the five ideas degrade or break without multi-platform volume.** Before building features:
1. Rotate OCR keys via `lib/keypool.py` (or back off / fail over to a second vision provider).
2. Add a min-iteration / min-corpus floor so the LLM can't `agent_stop` on thin data.
3. Re-check `REL_FLOOR=0.30` — it dropped 72/84 posts in the observed run.

A great feature on an empty corpus demos worse than a modest feature on rich data. Fix the funnel first.
