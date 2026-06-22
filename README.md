# sinai — MTN's live_docs instance

**sinai** is both the definition and the first live instance of **live_docs**, a self-documenting atomic-documentation system.

- **live_docs** is the portable system specification. Its defining documents are tagged `scope: [live_docs]`.
- **sinai** is MTN's instance of that system. Organisation-specific documents are tagged `scope: [sinai]` or a more specific domain.

The two coexist in this repo by design: the spec is proven by eating its own cooking.

---

## Contents

- [Install](#install)
- [How to read this repo](#how-to-read-this-repo)
- [kb/ layout](#kb-layout)
- [Inbox → raw → docs pipeline](#inbox--raw--docs-pipeline)
- [Frontmatter schema](#frontmatter-schema)
- [Edge types](#edge-types)
- [ldoc CLI](#ldoc-cli)
- [Skills](#skills)
- [cascade / validate / reindex / reviews](#cascade--validate--reindex--reviews)
- [Other directories](#other-directories)

---

## Install

live_docs has three independent parts. Only the store differs per project; the CLI and skills are installed once, globally.

| Part | What it is | Scope |
|------|-----------|-------|
| `ldoc` CLI | `scripts/ldoc.py`, symlinked onto your PATH | one machine-wide install; works in any terminal |
| `livedocs` skills | the Claude Code plugin in `.claude-plugin/` (exposes the `.claude/skills/`) | one user-scope install; available in every project |
| the **store** | the `kb/` graph, located by a `.living_doc.toml` marker | per consumer repo — just the marker file |

### Quick start

From inside this repo:

```bash
./install.sh                 # ldoc CLI on PATH + livedocs plugin (user scope)
```

That symlinks `ldoc` into `~/.local/bin` and runs `claude plugin marketplace add` + `claude plugin install livedocs@mtn-livedocs`. It's idempotent — safe to re-run. Restart any running Claude Code session afterward to pick up the skills. Useful flags: `--no-plugin` / `--no-cli` to install just one part, `--bin-dir DIR` to link `ldoc` elsewhere, `--init-store DIR` (see below). Run `./install.sh --help` for the full list.

After installing, the skills are namespaced under the plugin: `/livedocs:garden`, `/livedocs:ingest-reference`, `/livedocs:validate`, and so on.

### Pointing another repo at a store

The CLI and skills are store-agnostic: they operate on whichever store the current directory's `.living_doc.toml` points at. To make a *consumer* repo read/write a shared store (e.g. this one, or a dedicated docs repo), drop a marker file at its root:

```bash
cd /path/to/consumer-repo
/path/to/live_docs/install.sh --init-store /path/to/store   # writes .living_doc.toml
ldoc count                                                  # confirm it resolves
```

`--init-store` writes absolute paths into the store's `kb/`. You can also hand-write the four-line `.living_doc.toml` (see [kb/ layout](#kb-layout)) — the helper is just convenience.

### Manual / partial setup

If you'd rather not run the script, the two install steps are:

```bash
# CLI — any PATH dir works; ldoc.py is stdlib-only
ln -s /path/to/live_docs/scripts/ldoc.py ~/.local/bin/ldoc

# skills plugin
claude plugin marketplace add /path/to/live_docs
claude plugin install livedocs@mtn-livedocs        # --scope user is the default
```

Working *inside this repo*, `ldoc` is also provided via `mise` (`mise trust` once per machine) without any global install.

---

## How to read this repo

The knowledge base lives entirely in `kb/`. The flat `kb/02-docs/` store has no canonical "front page" yet — the root index doc (`kb/02-docs/20260615090011.md`) is currently a stub, intended to become the top-level index of the system's highest-level MOCs once that (agentic) concept is built.

Filenames are opaque timestamp IDs (Zettelkasten/"Kiste" style); the human-readable name lives only in the `title` frontmatter field. Navigate with `ldoc find` / `ldoc ls`, or by following typed edges from any doc you land on.

The authoritative source of truth is always the flat `*.md` files in `kb/02-docs/`. Generated artifacts under `kb/02-docs/.index/` are caches — rebuildable, never hand-edited.

---

## kb/ layout

```
kb/
  00-inbox/      # drop-point — instant, no-processing capture (gate 0)
  01-raw/        # verbatim clippings — accepted but not yet decomposed (gate 1)
  02-docs/       # the atomic graph — every doc is 02-docs/<id>.md
    .index/      # generated artifacts: dependents.json, referenced_by.json,
                 #   hierarchy.md, orphans.txt  (do not hand-edit)
  reviews/       # review ledger — post-hoc episode summaries
```

Paths are configured in a `.living_doc.toml` file, located by discovery: `ldoc` walks up from the working directory looking for one, falling back to `~/.config/living_doc/config.toml`. Paths inside it resolve relative to the config file's own directory (absolute and `~` honored), so the docs need not live in the same repo as the code that reads them — a single store can serve several related repos. Per-key `LIVEDOCS_*_DIR` environment variables override the file; omitted keys fall back to a root-layout. A deployment can relocate any box, or point at a shared store elsewhere, without touching code.

---

## Inbox → raw → docs pipeline

Capture is frictionless; ingestion is deliberate. Three gates:

| Gate | Command | What happens |
|------|---------|-------------|
| **0 — capture** | `ldoc inbox add` | Material dropped into `kb/00-inbox/` verbatim, no processing |
| **1 — accept** | `ldoc promote <ref>` | Inbox item moved to `kb/01-raw/` with raw-clipping frontmatter |
| **2 — ingest** | `ingest-reference` skill | Raw item decomposed into atomic docs in `kb/02-docs/` |

Gate 0 is instant: use it whenever you want to capture something without stopping to process it. Gate 1 is a conscious acceptance gate. Gate 2 is where atomicity is produced — it must not be skipped (a raw blob ingested as a single doc is a liability).

If a ref is already in `kb/01-raw/`, `ldoc promote` will tell you to run the `ingest-reference` skill instead.

---

## Frontmatter schema

### Canonical field order

```yaml
---
id:           "<14-digit timestamp, matches filename>"
title:        "<sentence-length human name>"
label:        "<Title Case 2–5 word identifier>"
summary:      "<1–3 sentence (≤~50 word) overview, mirroring the doc's opening>"
type:         <see enums below>
status:       <see enums below>
level:        <see enums below>
belongs_to:   ["[[<id>]]", ...]   # omit when empty
requires:     ["[[<id>]]", ...]   # omit when empty
relates:      ["[[<id>]]", ...]   # omit when empty
provenance:   ["[[<id>]]", ...]   # omit when empty
superseded_by: ["[[<id>]]", ...]  # omit when empty
domain:       [tag, ...]          # flat list; omit when empty
scope:        [tag, ...]          # flat list; omit when empty
created:      "<ISO 8601 UTC>"
history:                          # omit when empty; changes only, never creation
  - at: "<ISO 8601>"
    summary: "<what changed>"
---
```

Edge lists are stored as quoted wikilinks (`"[[<id>]]"`) for Obsidian graph compatibility. The tooling unwraps them to bare IDs in memory. Empty edge lists, empty `history`, and empty `domain`/`scope` are omitted entirely from the file — writing `[]` is wrong.

`reference` type docs also carry `kind`, `source`, and `imported` fields (appended after `history`).

### Three descriptors

Every doc has three human-facing descriptors with distinct roles:

| Field | Length | Purpose |
|-------|--------|---------|
| `label` | 2–5 words, Title Case | Short identifier for display and CLI ref resolution |
| `title` | Sentence-length | Human-readable name; the authoritative name of the concept |
| `summary` | 1–3 sentences, ≤ ~50 words | Tight overview mirroring the doc's opening; verbatim in review snapshots, search, and index maps |

### Enums

| Field | Valid values |
|-------|-------------|
| `type` | `type`, `principle`, `goal`, `decision`, `constraint`, `requirement`, `use-case`, `guide`, `component`, `reference`, `index` |
| `status` | `living` (current), `target` (intended-but-not-yet-built), `deprecated` (retired), `reference` (frozen supporting material) |
| `level` | `incidental` (calcified without a decision), `trial`, `preference`, `requirement` |

The 11 `type` values are the taxonomy, defined as enum values in `model.py`. (There are no separate per-type definition docs — earlier ones were removed as non-weight-bearing orphans, so the taxonomy lives in code, not as docs.)

The old `state: actual|target` field has been folded into `status` (`target` = intended-but-unbuilt; `living` = current reality). The old separate `state` field is stale schema.

---

## Edge types

| Edge | Direction | Cascade? | Semantics |
|------|-----------|----------|-----------|
| `requires` | outbound | **hard** | Existential dependency — this doc is meaningless without the target |
| `belongs_to` | outbound | **hard** | Structural parent — this doc is a child of the target (index → member) |
| `relates` | outbound | soft | Symmetric clustering / see-also; navigation only |
| `provenance` | outbound | soft | Immutable derivation lineage — "was derived from / informed by"; may point at `kb/01-raw/` |
| `superseded_by` | outbound | — | Deprecation pointer; required when `status: deprecated` |

**Reverse edges** (`dependents`, `provenance_of`) are generated by `reindex` and stored in `kb/02-docs/.index/`. Never hand-author them.

Cascade-hard edges (`requires` + `belongs_to`) drive `cascade-check` and the reverse-dependency map. `relates` and `provenance` are never cascade inputs.

**Deprecation rule**: setting `status: deprecated` is only valid if (a) `superseded_by` is non-empty AND (b) the doc body has a `## Correction` section explaining why it is wrong and what replaced it.

---

## ldoc CLI

`ldoc` is the porcelain CLI (`scripts/ldoc.py`). It must be on your PATH; this repo provides it via mise:

```bash
mise trust          # once per machine, first time in this repo
ldoc help           # grouped verb overview with copy-pasteable examples
```

Elsewhere, put `ldoc` on your PATH yourself (a symlink or thin wrapper to `scripts/ldoc.py`). It locates the store by discovery, so it runs from any directory that belongs to one.

All ref arguments accept `id`, `label`, or `title` (exact or unique substring). Most read verbs accept multiple refs space-separated; pass `-` as the sole ref to read from stdin.

### Verb groups

**Reads**

| Verb | What it does |
|------|-------------|
| `get <ref...>` | Frontmatter summary (id, label, title, type, status, level, history count) |
| `body <ref...>` | Print the body text |
| `show <ref...>` | Full doc: frontmatter + all resolved edge lists + history + body |
| `resolve <ref...>` | Resolve ref(s) to canonical id(s) |
| `label <ref...>` | Print `<Type>: <Title>` display string |
| `neighbors <ref...>` | All neighbors, optionally filtered by `--kind` |

**Search / list**

| Verb | What it does |
|------|-------------|
| `find [terms...] [--or] [--regex PAT]` | Full-text search + filter by `--type`, `--level`, `--status`, `--scope`, `--domain` |
| `ls [--type T]` | List all docs (optionally filtered by type) |
| `log [--since ISO] [--limit N]` | Recent changes view (created/edited, newest first) |
| `count` | Doc and edge count statistics by type / level / status |

**Graph**

| Verb | What it does |
|------|-------------|
| `graph <ref> [--depth N] [--direction up\|down\|both]` | BFS traversal |
| `edges [--json]` | Full forward and reverse edge maps; `dangling` key lists broken refs |

**Mutations**

| Verb | What it does |
|------|-------------|
| `new --type T --title T [options]` | Create a new doc (validates edge refs before writing) |
| `set <ref> [--title] [--label] [--summary] [--level] [--status] [--type] [--body -\|TEXT]` | Update frontmatter fields or body |
| `edit <ref>` | Alias for `set <ref> --body -` (replace body from stdin) |
| `link <ref> [--requires\|--belongs-to\|--relates\|--provenance\|--superseded-by a,b]` | Add edges |
| `unlink <ref> [same edge flags]` | Remove edges |
| `history <ref> --add "summary"` | Append a history entry (changes only — never a creation entry) |
| `ingest-raw --source S [--from-file P\|--body T\|-]` | Write verbatim content to `kb/01-raw/` |

**Inbox pipeline**

| Verb | What it does |
|------|-------------|
| `inbox add [--from-file P\|--body T\|-] [--title T] [--source S]` | Drop material into `kb/00-inbox/` instantly |
| `inbox list` | List items currently in the inbox |
| `promote <ref>` | Gate 1: move inbox item → `kb/01-raw/` with raw-clipping frontmatter |
| `promote --all` | Drain the entire inbox |

**Maintenance**

| Verb | What it does |
|------|-------------|
| `validate` | Read-only structural integrity check (see below) |
| `reindex` | Rebuild `kb/02-docs/.index/` artifacts |
| `edges [--json]` | Print full forward/reverse edge map |
| `review new\|list\|show\|sign` | Manage review summaries in the `kb/reviews/` ledger |

Most mutation verbs accept `--dry-run` to preview what would happen without writing.

### Quick examples

```bash
# Read a doc
ldoc show "Living over Stale"
ldoc get root-index batch-operations --json

# Search
ldoc find porcelain
ldoc find --type decision --status living
ldoc ls --type principle

# Create and link
ldoc new --type decision --title "Use UTC for all timestamps" --level preference
ldoc link <id> --requires <dep-id>

# Inbox pipeline
echo "rough idea" | ldoc inbox add --body - --title "Rough idea"
ldoc inbox list
ldoc promote <inbox-id>   # gate 1: inbox → raw
# then run /ingest-reference for gate 2

# Maintenance
ldoc validate
ldoc reindex
ldoc review new --since 2026-06-15T00:00:00Z
ldoc review sign <review-id> --as "Your Name"
```

---

## Skills

Skills are AI-agent procedures in `.claude/skills/*/SKILL.md`. They are thin wrappers that invoke the shared `ldoc` CLI and `scripts/` logic; judgment lives in the skill, not the script.

They ship as the **`livedocs` Claude Code plugin** (`.claude-plugin/`), so installing once (see [Install](#install)) makes them available in every project, namespaced as `/livedocs:<skill>` (e.g. `/livedocs:garden`). The table below lists the user-facing entry points; several internal sub-skills (`identify-key-concepts`, `map-concepts-to-docs`, `assess-blast-radius`, `synthesize-doc-changes`) are marked `user-invocable: false` and are driven by the entry points, not run directly.

| Skill | When to use |
|-------|-------------|
| **apply-to-docs** | Landing a user request or design plan into the KB: extracts concepts, maps blast radius across the graph, batch-synthesizes a coherent new state for all affected docs |
| **ingest-reference** | Bringing external material (meeting notes, RFCs, research, URLs) into the store: creates a raw clipping, a normalized reference doc, then decomposes into single-responsibility atomic docs |
| **revise-doc** | Editing an existing doc with full discipline: dedup/conflict scan, history entry, cascade-check for substantive changes |
| **cascade-check** | After one or more docs change, walk the dependency graph in both directions and decide which neighbors need updates; the primary consistency-enforcement mechanism |
| **garden** | Periodic maintenance: enforces Single Responsibility (decompose hot files), catches staleness, repairs orphans, normalizes schema drift |
| **validate** | Read-only mechanical integrity check — reports errors/warnings but fixes nothing; use before releases or after bulk edits |
| **reindex** | Rebuild `kb/02-docs/.index/` derived artifacts after bulk doc creation/deletion or graph restructuring |

---

## cascade / validate / reindex / reviews

### cascade-check

When any doc changes, `cascade-check` walks `requires` and `belongs_to` edges in both directions (upstream dependencies and downstream dependents) and issues a verdict per neighbor: `inconsequential`, `cascade`, `incompatible`, or `context-request`. The write pass is always batched after the full read pass — no interleaving.

A wide cascade (> 3 docs from one edit) is a design smell: the changed doc may carry more than one responsibility. The skill suggests running the `garden single-responsibility` pass.

### validate

`ldoc validate` checks:
- Required fields (`id`, `title`, `label`, `type`, `status`, `level`, `created`)
- Label format and uniqueness (case-insensitive across the store)
- Valid enum values for `type`, `status`, `level`
- `id` matches filename
- All `requires`, `belongs_to`, `relates`, `superseded_by` refs resolve to existing docs
- `provenance` refs that don't resolve are warnings (may point at `kb/01-raw/`)
- `reference` docs have `kind`, `source`, `imported`
- `deprecated` docs have non-empty `superseded_by`

Exits 0 if clean, 1 if errors. Use `garden consistency` for fix proposals.

### reindex

`ldoc reindex` rebuilds `kb/02-docs/.index/`:

- `dependents.json` — reverse map of `requires` + `belongs_to` edges (the cascade input)
- `referenced_by.json` — reverse map of `provenance` edges (navigation only)
- `hierarchy.md` — human-readable children rollup per index doc
- `orphans.txt` — docs with no hard graph edges in either direction

Run `reindex` after bulk doc changes, or before a cascade-check if you want a pre-built reverse map on hand. (`reindex` only writes derived caches under `.index/`; it does not edit doc bodies.)

### reviews

The review ledger (`kb/reviews/`) holds post-hoc episode summaries. Skills emit one summary per episode via `ldoc review new --since "$START"`. Reviews are non-gating — they never block a change; they record it for later signoff. Sign with `ldoc review sign <id> --as "Your Name"`.

---

## Other directories

| Path | Contents |
|------|----------|
| `scripts/` | All shared tooling: `ldoc.py` (porcelain CLI), `livedocs/` (KB layer), `validate.py`, `reindex.py` |
| `bin/` | `ldoc` symlink → `scripts/ldoc.py`; added to PATH via `mise.toml` |
| `install.sh` | One-shot installer: `ldoc` on PATH + the `livedocs` plugin (see [Install](#install)) |
| `.claude-plugin/` | `plugin.json` + `marketplace.json` — packages `.claude/skills/` as the installable `livedocs` plugin |
| `.claude/skills/` | AI-agent skill definitions (see Skills above) |
| `reports/` | Design analyses and research artifacts (not part of the KB graph) |
| `.obsidian/` | Obsidian vault configuration for visual graph navigation |
