# PulseTrace — 30+ Personas: Why Use It, Why Pay, Where the Revenue Is

> One engine (topic → agentic multi-source crawl → cluster → sentiment → influence rank →
> coordination/astroturf scan → cited RAG Q&A), sold into many markets. This doc enumerates
> the points of view a buyer can occupy, the pain that forces adoption, the trigger that forces
> *payment*, and the revenue mechanism that captures it.

## How to read each persona
- **POV** — the lens / who is speaking.
- **Pain** — what hurts today (the "do nothing" cost).
- **Why use** — the specific PulseTrace capability that fixes it.
- **Why pay** — the moment value exceeds the price; what they'd lose by going free/manual.
- **Revenue** — tier + monetization mechanism it maps to.

Pricing tiers referenced: **Starter** (~৳5k/$45), **Pro** (~৳20k/$180), **Enterprise**
(৳2L+/yr custom), **Usage/per-report** (pay-per-run), **BYOK self-serve** (thin platform fee,
user brings own API keys), **API/MCP metered** (per-call, agent-facing).

---

## Segment A — Commerce & Brand

### 1. E-commerce / D2C brand manager
- **Pain:** A product launch or flash sale either lands or flops; they find out from sales lag, days late, never knowing *why*.
- **Why use:** Topic = the SKU/brand → live sentiment timeline, theme clusters (shipping, price, quality, sizing), top complaining vs praising voices, all cited.
- **Why pay:** One avoided returns-wave or one fixed listing pays a year of Pro. Free manual scrolling can't cluster 500 posts or rank the loudest detractor.
- **Revenue:** **Pro** (recurring) + **Usage** spikes around launches.

### 2. Marketplace seller / Amazon-FBA-style operator
- **Pain:** Reviews and off-platform chatter (Reddit, FB groups) decide ranking; they read none of it at scale.
- **Why use:** Cross-source crawl surfaces complaints *before* they hit the review page; coordination scan flags competitor review-bombing.
- **Why pay:** Catching one fake-review campaign protects the buy-box; that's revenue, not vanity.
- **Revenue:** **Starter→Pro**, **per-report** during disputes.

### 3. Marketing / growth agency (servicing many clients)
- **Pain:** Manually building "social listening" decks for each client; juniors with 40 tabs.
- **Why use:** One topic per client → a queryable, re-askable asset + exportable briefing PDF. Multi-user OAuth = whole team.
- **Why pay:** Bills the report to *their* client at markup; PulseTrace is COGS with software margins.
- **Revenue:** **Pro / Enterprise** seats; agency is a reseller channel.

### 4. Performance / paid-media buyer
- **Pain:** Creative fatigue and narrative shifts kill ROAS, detected only after spend.
- **Why use:** Theme clustering shows *which* message is resonating vs souring in near-real-time.
- **Why pay:** A 1-day-faster pivot on a large ad budget dwarfs the subscription.
- **Revenue:** **Pro**, **API** (feed sentiment into bid automation).

### 5. Influencer / creator vetting (brand-side)
- **Pain:** Paying a creator whose audience is bots or whose sentiment is turning.
- **Why use:** Influence rank + coordination scan = is this voice organic and trusted, or inflated?
- **Why pay:** One avoided bad sponsorship = many months of fees.
- **Revenue:** **Usage / per-report** (vetting is episodic).

---

## Segment B — Media, Politics & Public Sphere

### 6. Newsroom / investigative journalist
- **Pain:** A story is "trending" — but is it real public sentiment or a manufactured push?
- **Why use:** Coordination/astroturf detection is the *headline feature*: same message, clustered accounts, tight window → "Coordinated Campaign Detected" with a confidence score. Every claim cited to a source post.
- **Why pay:** It *is* the story; it replaces days of manual OSINT. Cited Q&A = defensible, publishable evidence.
- **Revenue:** **Pro / Enterprise** (newsroom seats), public-good positioning.

### 7. Political campaign strategist
- **Pain:** Learns the narrative turned *after* it's lost.
- **Why use:** Opinion-mode seeding (half support / half challenge queries) maps both sides; astroturf radar = shield against opponents' bot waves.
- **Why pay:** Elections are won on timing; the cost is trivial vs a campaign budget.
- **Revenue:** **Enterprise** (seasonal, high-value), **per-report** rapid-response.

### 8. Government / policy analyst
- **Pain:** Public reaction to a policy is read by interns, in English, shipped to foreign tools.
- **Why use:** Local-first, in-country data sovereignty; sentiment + authenticity on the actual conversation.
- **Why pay:** Procurement requirement (data can't leave the country); recurring institutional contract.
- **Revenue:** **Enterprise** (annual license + SLA + custom dashboards).

### 9. Regulator / election-integrity body
- **Pain:** Coordinated misinformation is a state-level concern; no tooling to *prove* it.
- **Why use:** Coordination scan produces an auditable, scored artifact of inauthentic behavior.
- **Why pay:** Mandate-driven; public-good instrument; budget exists.
- **Revenue:** **Enterprise** / grant-funded deployment.

### 10. NGO / civil-society / fact-checker
- **Pain:** Misinformation harms communities; tiny budgets vs Western tool prices.
- **Why use:** Affordable astroturf + narrative tracking; cited evidence for debunks.
- **Why pay:** Grant line-item; far cheaper than incumbents.
- **Revenue:** **Starter / Usage**, discounted/grant tier.

---

## Segment C — Research, R&D & Knowledge Work

### 11. Academic researcher (comp-social-science, NLP, political science)
- **Pain:** Building a multi-platform social corpus by hand; reproducibility is a nightmare.
- **Why use:** 9 connectors behind one schema → uniform `Post` records, persisted per-run (posts.json, clusters.json, FAISS index) = a citable, re-runnable dataset.
- **Why pay:** Saves months of scraper plumbing; BYOK keeps grant costs predictable.
- **Revenue:** **BYOK self-serve**, academic tier; **API** for batch studies.

### 12. Corporate R&D / product-discovery team
- **Pain:** Voice-of-customer signal is scattered; feature decisions ride on gut feel.
- **Why use:** Cluster the chaos into themes; rank pain points by influence; ask "what do power users want?" with cited answers.
- **Why pay:** One correctly-prioritized roadmap item justifies it; integrates via API into the PM workflow.
- **Revenue:** **Pro / Enterprise**, **API** into internal tooling.

### 13. UX researcher
- **Pain:** Qual interviews are tiny-N; social is large-N but unstructured.
- **Why use:** Sentiment + theme clusters = large-N qualitative signal, cited and quotable.
- **Why pay:** Replaces expensive panel studies for discovery-phase questions.
- **Revenue:** **Usage / per-report** (per study) or **Pro**.

### 14. Data scientist / ML team (build-vs-buy)
- **Pain:** Wants embeddings + clustering + ranking but won't build the agent loop.
- **Why use:** 15 MCP tools + REST API expose the whole pipeline programmatically; cached embeddings.
- **Why pay:** Cheaper than building/maintaining; metered calls scale with usage.
- **Revenue:** **API/MCP metered**, **BYOK**.

### 15. Competitive-intelligence / strategy analyst
- **Pain:** Tracking rivals across platforms manually; stale by the time it's compiled.
- **Why use:** Topic = competitor → themes, sentiment, top voices, coordination flags (are they astroturfing?).
- **Why pay:** Standing intelligence asset, re-askable forever; persistent run history.
- **Revenue:** **Pro / Enterprise** (always-on monitoring).

---

## Segment D — Finance, Risk & Trust

### 16. Hedge fund / retail-trading analyst (sentiment alpha)
- **Pain:** Social sentiment moves tickers; manual reading doesn't scale or timestamp.
- **Why use:** Sentiment timeline + influence-weighted signal + Polymarket connector (prediction-market priced odds) in one view; alert webhook on viral spikes (peak ≥0.75).
- **Why pay:** Latency-sensitive edge; API feed into a model is worth far more than a seat.
- **Revenue:** **API metered** (highest willingness-to-pay), **Enterprise**.

### 17. VC / startup scout
- **Pain:** Gauging real traction vs manufactured hype around a startup/founder.
- **Why use:** Authenticity layer separates organic momentum from coordinated shilling.
- **Why pay:** One de-risked or avoided deal pays for years.
- **Revenue:** **Pro**, **per-report** (diligence bursts).

### 18. Crypto / Web3 community & token team
- **Pain:** Pump-and-dump and bot shilling are endemic; hard to know real community health.
- **Why use:** Coordination scan is purpose-built for exactly this; cross-source (X, Reddit, Bluesky) sentiment.
- **Why pay:** Reputational + regulatory exposure; ongoing monitoring.
- **Revenue:** **Pro / API**, usage spikes around launches.

### 19. Insurance / underwriting (reputational & event risk)
- **Pain:** Pricing reputational-risk and event-driven exposure with no live signal.
- **Why use:** Real-time sentiment + virality alerts as a risk input.
- **Why pay:** Feeds pricing models; institutional contract.
- **Revenue:** **Enterprise / API**.

### 20. Cybersecurity / threat-intelligence (influence ops)
- **Pain:** Detecting coordinated inauthentic behavior / information operations.
- **Why use:** Astroturf detection + clustered-account timing analysis = an IO-detection primitive.
- **Why pay:** Core to the SOC/threat-intel mandate; API integration.
- **Revenue:** **Enterprise / API metered**.

---

## Segment E — Operations, PR & Customer-Facing

### 21. PR / crisis-comms lead
- **Pain:** A PR fire is found only when it's already trending.
- **Why use:** Viral-spike alert (n8n webhook) + theme breakdown of *what exactly* people are angry about, cited.
- **Why pay:** Minutes-not-days response window; one managed crisis justifies the year.
- **Revenue:** **Pro / Enterprise**, **per-report** in crises.

### 22. Customer-support / CX operations
- **Pain:** Off-channel complaints (social) never reach the ticket queue.
- **Why use:** Cluster complaints by theme; rank by influence; ask "top unresolved issues this week?"
- **Why pay:** Deflects escalations, finds systemic bugs early; API into the helpdesk.
- **Revenue:** **Pro**, **API**.

### 23. HR / employer-brand / recruiting
- **Pain:** Glassdoor + social employer sentiment is unmonitored; affects hiring funnel.
- **Why use:** Topic = company-as-employer → sentiment themes, authenticity check on review bombs.
- **Why pay:** Recruiting cost-per-hire is high; reputation directly affects it.
- **Revenue:** **Starter / Pro**.

### 24. Market-research firm (reseller)
- **Pain:** Clients want social insight; building it in-house is costly.
- **Why use:** White-labelable engine + exportable reports; BYOK keeps margins.
- **Why pay:** Resells at markup; PulseTrace is wholesale infrastructure.
- **Revenue:** **Enterprise / API** (channel/wholesale).

### 25. Management consultant
- **Pain:** Needs fast, defensible market/opinion evidence for client decks.
- **Why use:** Cited Q&A → quotable, source-linked evidence on demand.
- **Why pay:** Billable hours saved; per-engagement bursts.
- **Revenue:** **Per-report / Pro**.

---

## Segment F — Verticals & the Long Tail

### 26. Tourism board / destination marketing
- **Pain:** Perception of a destination shifts with events; no live read.
- **Why use:** Multi-source sentiment + theme tracking on the destination.
- **Revenue:** **Pro / Enterprise** (institutional).

### 27. Entertainment / film / music / streaming
- **Pain:** Pre- and post-release reception, and astroturfed review campaigns.
- **Why use:** Sentiment timeline around release + coordination scan on review waves.
- **Revenue:** **Pro / per-report** (per title).

### 28. Sports club / league / athlete management
- **Pain:** Fan sentiment, transfer rumors, sponsorship-risk monitoring.
- **Why use:** Live sentiment + top-voice ranking + rumor-source authenticity.
- **Revenue:** **Pro**, seasonal **Enterprise**.

### 29. Healthcare / pharma / public-health comms
- **Pain:** Vaccine/treatment misinformation and coordinated anti-health campaigns.
- **Why use:** Astroturf detection + narrative clustering = public-health early warning.
- **Revenue:** **Enterprise** (regulated, high-value).

### 30. AI-agent builder / platform developer (the "picks-and-shovels" buyer)
- **Pain:** Their agent needs real-time, *verified* social intelligence; no clean API exists.
- **Why use:** 15 standardized MCP tools — start a crawl, get sentiment, run coordination scan, ask cited questions — all machine-callable.
- **Why pay:** Cheaper and faster than building; metered per call; this is the long-game agent-native market.
- **Revenue:** **API/MCP metered** + **BYOK** — near-zero marginal cost, viral developer top-of-funnel.

### 31. Brand / legal — IP & counterfeit / defamation monitoring
- **Pain:** Counterfeit pushes and defamation campaigns spread on social, undocumented.
- **Why use:** Cross-source detection + cited evidence trail + coordination scan = takedown/legal exhibit.
- **Revenue:** **Per-report / Enterprise** (legal budgets are deep).

### 32. Educator / media-literacy program
- **Pain:** Teaching "is this real?" with no live tooling.
- **Why use:** Coordination scan as a teaching instrument; affordable.
- **Revenue:** **Starter** / education tier.

---

## Revenue model — how the personas roll up

| Mechanism | Who pays | Why it captures value |
|---|---|---|
| **SaaS subscription** (Starter/Pro/Enterprise) | brands, agencies, newsrooms, campaigns, CX, HR, vertical institutions | recurring MRR; always-on monitoring is sticky; multi-user seats expand accounts |
| **Usage / per-report** | consultants, VCs, vetting, crisis, legal, episodic researchers | low-friction entry; captures spiky, high-intent demand without a commitment |
| **Enterprise contracts** | govt, regulators, pharma, finance, large brands/media | annual license + SLA + custom dashboards + data-sovereignty; highest ACV |
| **BYOK self-serve** | researchers, developers, global long-tail | user pays inference; PulseTrace takes a thin platform fee at near-zero marginal cost; viral top-of-funnel |
| **API / MCP metered** | quant funds, threat-intel, agent-builders, market-research resellers, R&D | per-call billing scales directly with value; the agent-native long game |

### The margin story (why VCs underwrite it)
Marginal cost per analysis is a few cents of LLM + embedding calls, and embeddings are
**SHA-keyed and cached** (`embed_cache.jsonl`) so re-runs trend toward free. BYOK pushes
inference cost entirely onto the user. Result: software-grade gross margins on an intelligence
product, improving with scale rather than eroding.

### The three durable "why pay" triggers (cut across all personas)
1. **Timing** — minutes-not-days detection of a shift/fire/spike; the cost of being late dwarfs the price.
2. **Authenticity** — the coordination/astroturf moat answers "is this even real?", the scarce signal in the bot era. No incumbent offers it.
3. **Persistence + programmability** — every run is a stored, re-askable asset and an API/MCP surface, so value compounds instead of evaporating after one brief.

---

## One-line per buyer (the elevator version)
> "Whoever's outcome is decided by public opinion — a brand's sales, a campaign's vote, a
> fund's position, a regulator's mandate, a researcher's dataset, or another AI agent's input —
> PulseTrace tells them *what people think, who moved it, and whether it's real* — cited, live,
> and queryable. They pay because being late or being fooled costs far more than the subscription."
