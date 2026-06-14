# PulseTrace — Path to a Usable Product + Quick-Earning Pivots

> Companion to `2026-06-12-personas-why-pay.md`. That doc says *who pays and why*.
> This doc says *what's blocking us from charging them today*, and *which slice ships
> revenue fastest with the least new build*.
>
> Stance: be honest about what's demo-grade vs. production-grade. Every pivot below is
> scoped to reuse the engine we already have, not a rewrite.

---

## Part 1 — What we actually have (verified)

**Engine (real, deployed at pulsetrace.publicvm.com):**
- Topic → agentic multi-source crawl → embed → cluster → label → sentiment timeline →
  influence/voice ranking → coordination/astroturf scan → cited RAG Q&A → conversational chat.
- Connectors: Reddit, HN, Polymarket (reliable, on by default). YouTube, Bluesky, GitHub
  (wired). X, Instagram, Facebook (fragile / creds-gated).
- Auth (Supabase GoTrue + Google/GitHub OAuth), per-user isolation, BYOK key flow.
- Persistent chat + run history (Supabase). 15 MCP tools. Briefing PDF export.
- ~394 tests. Relevance gate + reranking (+38–72% nDCG). Dedup (simhash). Key failover pool.

**Translation:** the hard part is done. The product *works*. What's missing is the layer
between "works for the builder" and "a stranger pays and stays."

---

## Part 2 — Blockers to a usable product

Ranked by how hard they block a paying stranger. Each is a gate, not a nice-to-have.

### Tier 0 — Trust & reliability (without these, no one pays twice)
1. **Source honesty in the UI.** X/IG/FB silently return `[]` when uncredentialed. A paying
   user reads that as "no results / broken." Fix: per-source status badges (live / degraded /
   needs-auth / off), and never show an empty timeline without saying *why* it's empty.
2. **Run reproducibility.** Same topic twice → different crawl span/sources → different answer.
   Buyers distrust that. Fix: pin + display the crawl window, source set, and post count on
   every run; let them re-run with the same config.
3. **Latency honesty.** ~36–62s/run with LLM overhead. Fine for a deep report, fatal for a
   "type and watch" expectation. Fix: either (a) frame it as a *report* (async, email/notify
   when ready) or (b) progressive reveal that feels alive (partly shipped: live build).
4. **Cost ceiling per run.** A runaway agent loop on someone's BYOK key = an angry user.
   Fix: hard per-run token/$ cap, surfaced before they hit run, enforced server-side.

### Tier 1 — Monetization plumbing (no money without these)
5. **Billing.** Stripe + plan gating. Even one tier. Today there's no way to *take money*.
6. **Usage metering + quotas.** Per-account run counts, source caps, seat limits. The personas
   doc sells Starter/Pro/Enterprise/metered — none enforceable until metered.
7. **Onboarding that doesn't need the builder.** First-run wizard: pick a topic from examples,
   see a result in <60s, hit a paywall at the *second* valuable action. No README required.

### Tier 2 — Stickiness (turns a trial into a subscription)
8. **Saved topics + scheduled re-runs.** "Watch this brand weekly, email me deltas." This is
   the difference between a one-off toy and a monitoring subscription. (Crawl engine exists;
   need scheduler + diff + notify.)
9. **Alerts.** Sentiment drop, volume spike, new coordinated cluster → push/email. The
   coordination scan already produces the signal; wire it to a trigger.
10. **Shareable / exportable output.** A link or PDF the buyer forwards to *their* boss. PDF
    briefing exists — make it a first-class, branded, link-shareable artifact.

### Tier 3 — Operational survival
11. **Single-node fragility.** One box, no durable queue. Fine at 10 users, breaks at 100.
    Don't pre-build for scale we don't have — but put crawls on a background worker/queue so a
    slow run can't wedge the web process.
12. **Connector rot.** FB/IG/X scraping breaks silently and often. Either lean on the stable
    sources (Reddit/HN/YouTube/Polymarket/Bluesky) as the *product*, or budget ongoing
    maintenance. Don't sell a source we can't keep alive.
13. **Abuse / legal surface.** Scraping ToS, PII in stored posts, BYOK key custody. At minimum:
    ToS, a takedown path, and don't persist raw PII we don't need.

**Minimum sellable cut (the real MVP):** Tier 0 (#1–4) + Tier 1 (#5–7) + #8 (saved/scheduled).
Everything else is post-revenue. That's the line.

---

## Part 3 — Quick-earning pivots (ranked by speed-to-cash)

Each pivot = a narrow wedge of the existing engine sold to one buyer who already has budget.
The rule: **least new build, sharpest pain, fastest to a paid pilot.**

### Pivot A — Astroturf / Coordination Radar  *(fastest, most differentiated)*
- **What:** Sell the coordination-detection scan as a standalone "is this campaign organic or
  manufactured?" report. Brands, PR firms, political teams, trust-&-safety, crypto/launch teams.
- **Why now:** It's the one feature competitors (Brandwatch, Mention, Sprout) *don't* have as a
  first-class output. We already built `detect_coordination`.
- **Build delta:** ~small. Wrap the scan in a one-page report + a confidence score + evidence
  posts. Sell per-report ($200–2k) before building any subscription.
- **First dollar:** pay-per-report, no billing infra needed — invoice manually for first 5 pilots.

### Pivot B — Reputation / Brand Monitor for SMBs & D2C
- **What:** "Watch my brand across Reddit/HN/YouTube, email me weekly + alert on spikes."
  Personas A1–A2. Undercut $X00–$X,000/mo incumbents at $45–180/mo.
- **Why now:** Biggest TAM, clearest "do nothing" cost, recurring by nature.
- **Build delta:** needs #8 scheduled re-runs + #9 alerts + #5 billing. Medium.
- **First dollar:** Pro subscription. Requires the monitoring loop — 2–3 weeks of focused build.

### Pivot C — Niche Deal/Signal Intelligence  *(highest price per seat)*
- **What:** Point the *stable* sources at one vertical that pays for an edge:
  - **VC/PE:** dev-tool & startup sentiment on HN/Reddit → sourcing/diligence signal.
  - **Trading:** Polymarket + social sentiment → prediction-market edge.
  - **Product/DevRel:** sentiment on a specific tool/SDK vs. competitors.
- **Why now:** these buyers pay 10× consumer prices for a defensible signal, and our reliable
  sources (HN/Reddit/Polymarket) are exactly where these conversations live. No fragile scraping.
- **Build delta:** mostly packaging + a curated topic template per vertical. Small–medium.
- **First dollar:** high-ticket pilot ($1–5k) or per-seat. Concierge-deliver the first ones.

### Pivot D — API / MCP as the product  *(developer/agent channel)*
- **What:** Sell the 15 MCP tools + REST as metered infra. "Sentiment & coordination as an API
  for *your* agent." Persona: AI builders, agent platforms.
- **Why now:** MCP is hot, the tools are real and pipeline-wired, and agent-facing buyers
  self-serve (low support cost). Distribution via MCP directories is nearly free.
- **Build delta:** API keys + metering + rate limits + docs. Medium (reuses #6).
- **First dollar:** metered per-call. Needs metering before it can bill.

### Pivot E — One-shot "Deep Report" product  *(no subscription, no stickiness needed)*
- **What:** Sidestep the latency/monitoring problem entirely. User types a topic, pays per
  report, gets an async branded PDF (sentiment + themes + voices + coordination + cited Q&A).
- **Why now:** It's literally what the engine produces today. Turns our *weakness* (slow, deep)
  into the *pitch* (thorough, async). Lowest build delta of all.
- **Build delta:** smallest — paywall the existing PDF briefing + async delivery + Stripe checkout.
- **First dollar:** Gumroad/Stripe one-time. Could ship this week.

---

## Part 4 — Recommended sequence

1. **This week — Pivot E (per-report) + Pivot A (coordination report).** Both are packaging,
   not engineering. Manual invoicing for first pilots → proves willingness-to-pay *before*
   building billing. This is the fastest honest path to the first $.
2. **Weeks 2–3 — Tier 0 trust fixes (#1–4) + Stripe (#5) + metering (#6).** Now reports are
   trustworthy and self-serve-payable.
3. **Weeks 3–5 — Pivot B monitoring loop (#8 + #9).** Converts one-off buyers into MRR. Pick
   ONE vertical from Pivot C to template first (recommend VC/dev-tool — stable sources, high price).
4. **Later — Pivot D API/MCP.** Once metering is solid, open the agent channel.

**The single highest-leverage move:** package the coordination scan as a paid one-page report
(A+E). It's differentiated, the build is near-zero, and it validates pricing without committing
to the subscription buildout. Everything else follows from whether strangers pay for that.

---

## Part 5 — Honest non-starters (don't chase these for quick cash)
- **Don't** sell Facebook/Instagram/X coverage as a headline feature — it rots and will burn trust.
- **Don't** build durable DB / multi-region / Docker before there's load (CLAUDE.md non-goals agree).
- **Don't** compete on breadth with Brandwatch — compete on the one thing they lack (coordination)
  and on price for SMBs they ignore.
- **Don't** promise real-time — we're a deep-report engine. Sell the depth, schedule the cadence.
