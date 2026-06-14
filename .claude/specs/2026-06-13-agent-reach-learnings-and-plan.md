# Agent-Reach — What to Steal, Agent-Wrap Plan, and the Connector Way

> Source studied: `Agent-Reach/` (v1.5.0, MIT) — a Python installer/doctor/router that
> gives AI agents access to 13 platforms. This doc records what is genuinely worth
> stealing for PulseTrace, a concrete plan to make PulseTrace installable across agents
> (Claude Code / Cursor / Windsurf / Codex / Copilot), and a connector hardening plan.
>
> Branches: agent-wrap work → `feat/agent-wrap`; connector work → its own branch later.
> Independent of `feat/improved_scan`.

---

## Part 0 — What Agent-Reach actually is (so we copy the right thing)

Agent-Reach is **not a scraper**. Its channels never fetch data. A channel only:
- `can_handle(url)` — does this URL belong to me?
- `check(config)` — probe an **ordered backend list**, pick the first healthy one, set
  `active_backend`, return `(status, message)` where status ∈ `ok | warn | off | error`.

The **agent itself** runs the upstream CLI (`twitter search`, `yt-dlp`, `gh`). Distribution
is a `SKILL.md` + a tiny MCP server (only `get_status`) + a one-command install that wires
those into whatever agent you use.

PulseTrace is the opposite kind of program: a **server pipeline** that needs posts as data
in-process, and it is itself a service agents call (it already ships a 15-tool MCP server +
5 skills). So we copy **patterns**, not architecture.

---

## Part 1 — Ideas to steal (honest scorecard)

| Dimension | Agent-Reach | PulseTrace today | Verdict |
|---|---|---|---|
| X/Twitter collection | `twitter-cli`, cookie auth, subprocess | `twikit`, cookie auth, in-process | **Tie** — same technique; in-process suits our pipeline |
| Connector reliability | ordered backends + live probe + fallback | single path, silent `[]` on failure | **Steal** ✅ |
| Source status visibility | `doctor`: per-source ok/warn/off + fix hint | none — silent empty | **Steal** ✅ |
| Generic web read | Jina Reader (`r.jina.ai/URL`), zero-config | none | **Steal** (minor) ✅ |
| Web semantic search | Exa via mcporter | none | Optional new source |
| Agent integration engine | Skill + status-only MCP | **full 15-tool MCP + 5 skills** | **We win** |
| Multi-agent install/config | one command, all agents, doctor | manual MCP wiring | **Steal** ✅ |
| Analysis (cluster/RAG/sentiment/coordination) | none | full | **We win** ✅✅ |

**Three things to steal, ranked:**
1. **Multi-agent install + `doctor`** (Part 2) — we have the MCP engine, we lack the
   one-command distribution Agent-Reach nails.
2. **Connector health-probe + ordered fallback + status reporting** (Part 3) — kills the
   silent-`[]` problem; directly fulfils Tier-0 #1 of the product-readiness doc.
3. **Jina Reader** as a zero-config web/article source + optional **Exa** web search (Part 3).

**Do NOT copy:** their installer-as-product architecture; swapping `twikit`→`twitter-cli`
(lateral, adds a subprocess dependency for no gain in an in-process pipeline).

---

## Part 2 — Agent-Wrap Plan (make PulseTrace installable everywhere)

**Goal:** one command emits/writes the MCP-client config that registers PulseTrace's MCP
server into any agent, plus a `doctor` that verifies it will actually run. We already have
`mcp_server.py` (FastMCP, stdio + `streamable-http`); we only need the distribution layer.

### What we ship
- `lib/agentwrap.py` (pure logic) + a CLI (`python -m lib.agentwrap` or a `main.py` subcommand).
- A generated **`SKILL.md`** (mirrors our existing `pulse*` skills) for Skills-aware agents.
- Docs page `docs/agent-setup.md` with copy-paste blocks per agent.

### The server command we register
```
command: <repo>/.venv/bin/python
args:    ["mcp_server.py"]
cwd:     <repo>
env:     OPENAI_API_KEY, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET (only those set)
```
Remote/HTTP option: `PULSETRACE_MCP_TRANSPORT=streamable-http` + URL form for hosted use.

### Per-agent config targets (schemas differ — generator handles each)
| Agent | File | Schema key | Notes |
|---|---|---|---|
| Claude Code | `claude mcp add` CLI **or** `.mcp.json` (project) | `mcpServers` | prefer the CLI; fall back to writing `.mcp.json` |
| Claude Desktop | `claude_desktop_config.json` | `mcpServers` | OS-specific path |
| Cursor | `~/.cursor/mcp.json` or `.cursor/mcp.json` | `mcpServers` | same shape as Claude |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | `mcpServers` | same shape |
| VS Code / Copilot | `.vscode/mcp.json` | `servers` | different key; entries take `type: "stdio"` |
| Codex | `~/.codex/config.toml` | `[mcp_servers.pulsetrace]` | TOML, not JSON |

### Commands
- `agentwrap print [--agent X]` — print the snippet(s); **default, mutates nothing** (safe).
- `agentwrap install [--agent X]` — write/merge into the agent's config file (idempotent merge;
  never clobber unrelated servers; back up the file first).
- `agentwrap doctor` — checks, each returns `ok | warn | error` + fix hint:
  - `mcp` importable; `mcp_server.py` imports without error; FastMCP present.
  - required env keys present (warn → which are missing + how to set).
  - venv python resolvable; chosen transport valid.
  - which agents are detected on this machine (config file exists) → suggest `install`.

### Tasks (TDD where pure)
1. `mcp_config(python, repo, env_keys) -> dict` + `render(agent) -> str` (JSON/TOML per target). Unit-tested.
2. `AGENT_TARGETS` registry (path + schema flavor) + `detect_agents()`.
3. `install(agent)` — safe idempotent merge with backup; tested on a tmp file.
4. `doctor()` — structured status list (mock missing deps/env). Tested.
5. CLI wiring + `docs/agent-setup.md` + generated `SKILL.md`.
6. `pip install -e .` entrypoint (`pyproject` console_script `pulsetrace-agentwrap`) so it's one command.

### Non-goals
No auto-installing system packages. No telemetry. `print` is the default; `install` only on request.

---

## Part 3 — The Connector Way (health, fallback, status, new sources)

**Problem:** `lib/connectors/*` fetch on a single path and return `[]` silently when a source
is unconfigured/broken. The UI then shows an empty result with no reason — reads as "broken."

**Steal Agent-Reach's channel contract**, adapted to our fetch-in-process model.

### New `Connector` contract (extends, not replaces, `fetch`)
```python
@dataclass
class SourceStatus:
    state: str          # "ok" | "needs_auth" | "off" | "error"
    backend: str | None  # which backend is active (e.g. "twikit", "praw", "rss")
    message: str         # human fix hint ("export X_COOKIES…", "set REDDIT_CLIENT_ID")

class Connector(ABC):
    name: str = "base"
    backends: list[str] = []                  # ordered: backends[0] preferred
    def fetch(self, query, limit=50) -> list[Post]: ...
    def status(self) -> SourceStatus: ...     # probe WITHOUT a full crawl
```

### Ordered-fallback fetch
Each connector tries its backends in order; first that yields wins; record `active_backend`.
Example mappings (probe-then-use, mirroring Agent-Reach's "reorder the list, don't rewrite"):

| Connector | Ordered backends | Status signal |
|---|---|---|
| reddit | praw/RSS (current) ▸ — | ok (always-on) |
| hn | Algolia API | ok |
| x | twikit(cookie) ▸ (optional) twitter-cli | `needs_auth` if no cookie/login |
| youtube | yt-dlp (current) | ok |
| facebook | playwright+cookies (current) | `needs_auth` if no `info/cookies.json` |
| instagram | current ▸ — | `needs_auth`/`off` |
| polymarket / github / bluesky | current | ok |
| **web (new)** | **Jina Reader** `r.jina.ai/URL` | ok, zero-config |
| **websearch (new, optional)** | **Exa** | `needs_auth` (free key) |

### Surface status (the actual user-facing win)
- `run.json` / SSE gains a `sources` block: `[{name, state, backend, message}]`.
- Agent loop publishes a `source_status` event before/while gathering.
- UI shows a **per-source badge**: 🟢 live · 🟡 needs-auth · ⚪ off · 🔴 error — and never
  renders an empty result without the reason (Tier-0 #1 from the product-readiness doc).
- MCP: add a `get_source_status` tool so agents can see why a source returned nothing.

### Tasks (TDD where pure)
1. `SourceStatus` + `status()` on `Connector`; default impl returns `ok`.
2. Implement `status()` per connector (probe: cookie file exists? key set? cheap HEAD/ping).
3. Ordered-fallback wrapper in `fetch` for multi-backend connectors (x, facebook).
4. New `web` connector (Jina Reader) — pure URL→markdown→Post; unit-tested with mocked HTTP.
5. (Optional) `websearch` connector (Exa) behind a key.
6. Thread statuses into `run.json` + SSE; add `get_source_status` MCP tool; UI badges.

### Non-goals
No scraping sources we can't keep alive as headline features (FB/IG stay best-effort with
honest `needs_auth`/`off` status). No new heavy deps beyond `requests` (Jina/Exa are HTTP).

---

## Sequencing
1. **Part 2 (agent-wrap)** on `feat/agent-wrap` — highest leverage, self-contained, no pipeline risk.
2. **Part 3 (connectors)** on a fresh branch — `status()` + badges first (the real win), then
   Jina web source, then optional Exa.
3. Each part = its own spec→plan→PR into `shyan`.

## One-line summary
Steal their **distribution** (one-command multi-agent install + doctor) and their **connector
resilience** (ordered fallback + honest per-source status), not their architecture. We already
out-class them on the MCP engine and analysis.
