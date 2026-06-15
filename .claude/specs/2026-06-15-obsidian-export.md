# Spec — Obsidian Export (second-brain)

> Status: MVP, export-only. Branch `feat/obsidian`. Import (vault → source) is phase 2, out of scope here.

## Why
PulseTrace already produces a knowledge graph: clusters (talking points) + similarity
edges + evidence claims. Obsidian renders exactly this shape natively (notes +
`[[wikilinks]]` + graph view). Exporting a run as a markdown vault turns each run into
durable second-brain notes that accrue and cross-link across runs (same topic next week
links back to old notes by filename).

## Scope (MVP)
- Pure builder: run data → `dict[relpath -> markdown]`.
- Server endpoint streams it as a `.zip` the user drops into any Obsidian vault.
- Dashboard button next to "Download briefing PDF".
- No import, no live sync, no Obsidian plugin.

## Data sources (existing, per run)
- `run.json`: `id, topic, sources, finished_at, metrics{posts,clusters}`.
- `clusters.json[]`: `id, label, desc, centroid, members[], sentiment{pos,neu,neg}, top_posts[]`.
- `posts.json[]`: `id, source, text, author, url, reactions, comments, ts`.
- `evidence.json` (optional): `claims[]{text, side, confidence, evidence_strength, reasoning, cluster_ids[], cluster_label}`.
- Edges: cosine(centroid_a, centroid_b) > 0.5 (same threshold as `/graph`).

## Vault layout
```
PulseTrace - <topic> (<run_id>)/
  _index.md                 MOC: run frontmatter, metrics, links to all notes
  clusters/<slug>.md        one per talking point
  claims/<slug>.md          one per evidence claim (omitted if no evidence)
```
Wikilinks target bare filename (Obsidian resolves vault-wide), so slugs must be unique +
stable. Slug = kebab(label); on collision append `-<id>`.

## Note shapes
**Cluster** — frontmatter `type: talking-point, run, topic, posts, sentiment_{pos,neu,neg},
mood, created, tags:[pulsetrace, talking-point]`. Body: desc, mood line
(`50% positive · 50% neutral · … · N posts`), `## Related talking points` (wikilinks with
% similar from edges), `## Representative posts` (top_posts: quote — source, reactions).

**Claim** — frontmatter `type: claim, run, side, confidence, evidence_strength, cluster, tags`.
Body: text as H1, side/confidence/strength line, reasoning blockquote, `Backs:` wikilink to
the cluster(s) it cites.

**_index (MOC)** — frontmatter `type: pulsetrace-run, run, topic, posts, clusters, sources,
created, tags:[pulsetrace, moc]`. Body: summary line, `## Talking points` list (wikilink —
posts, mood), `## Claims` list (wikilink — side, confidence).

`mood`: pos>neg+0.05 → positive; neg>pos+0.05 → negative; else mixed.

## Module / endpoint
- `lib/obsidian.py`: `build_vault(run, clusters, posts, evidence) -> dict[str,str]` (pure,
  TDD). Helpers: `_slug`, `_mood`, `_edges(clusters)`, note builders. ~200 LOC cap.
- `server.py`: `GET /run/<run_id>/obsidian` → owner-gated → zip the dict in-memory
  (`io.BytesIO` + `zipfile`) → `send_file` attachment `<topic>-obsidian.zip`.
- Frontend: button in app header; reuse `downloadBriefing` blob pattern.

## Tests (`tests/test_obsidian.py`, pure)
- frontmatter keys present on each note type
- edge > 0.5 → wikilink in both related sections; ≤ 0.5 → none
- slug collision appends id
- empty evidence → no `claims/`, MOC omits Claims section, no error
- mood thresholds (positive / negative / mixed)
- every wikilink target resolves to an emitted filename (no dead links)

## Non-goals
Import, sync, Dataview queries, per-user vault merging, attachments/images.
