# AGENTS.md — Operating manual for AI agents in this repo

This document is the operating manual for any AI agent working in the sinai/live_docs repo. Read it before touching anything in `kb/`.

For background on the system's design, see [README.md](README.md).

---

## Contents

- [Golden rule: use the ldoc porcelain](#golden-rule-use-the-ldoc-porcelain)
- [Docs-first principle](#docs-first-principle)
- [Which skill to invoke and when](#which-skill-to-invoke-and-when)
- [Schema rules an agent must respect](#schema-rules-an-agent-must-respect)
- [Edge rules](#edge-rules)
- [History rules](#history-rules)
- [Inbox pipeline: capture vs ingest](#inbox-pipeline-capture-vs-ingest)
- [Deprecation protocol](#deprecation-protocol)
- [Validate and reindex checkpoints](#validate-and-reindex-checkpoints)
- [Review summaries](#review-summaries)

---

## Golden rule: use the ldoc porcelain

**Never hand-parse or hand-edit doc files. Never use `cat`, `jq`, or ad-hoc JSON to read the KB. Never write raw frontmatter by hand.**

All KB access goes through the `ldoc` CLI:

```bash
ldoc get <ref>          # read frontmatter
ldoc show <ref>         # read frontmatter + edges + body
ldoc find <terms>       # search
ldoc new ...            # create a doc
ldoc set <ref> ...      # update frontmatter fields
ldoc link / unlink ...  # add / remove edges
ldoc history <ref> --add "..."   # append a history entry
ldoc validate           # check integrity
ldoc reindex            # rebuild .index/ artifacts
```

The `ldoc` porcelain must be on your PATH; inside this repo mise provides it. It locates the store by walking up from the working directory for `.living_doc.toml`, so it runs from any directory that belongs to a store.

**Mutators are intentionally dumb** — they write what you tell them and validate refs, but they do not judge impact, cascade propagation, or cross-doc consistency. That judgment lives in the skills. Always invoke the appropriate skill when making substantive changes; do not call ldoc mutations directly as a substitute for running the skill.

All ref arguments accept `id | label | title` (exact or unique substring). Pass `-` as the sole ref to read from stdin.

---

## Docs-first principle

**Plan and record changes in docs before or as you implement them.** If a decision is being made, it belongs in a `decision` doc. If a constraint is being discovered, it belongs in a `constraint` doc. If a design is being introduced, extract its concepts via `apply-to-docs` before writing code or configuration.

The KB is not a changelog; it is the living model of what the system IS. Implementation that races ahead of the KB creates drift — the primary enemy of the system. Drift spreads faster than it is repaired.

---

## Which skill to invoke and when

Skills are in `.claude/skills/*/SKILL.md`. Each skill owns a specific operating procedure. Invoke the matching skill; do not approximate it with raw ldoc calls.

| Situation | Skill to invoke |
|-----------|----------------|
| A user request, design proposal, or plan needs to be recorded in the KB | **apply-to-docs** |
| External material needs to be brought in (meeting notes, RFC, article, research, URL content) | **ingest-reference** |
| An existing doc needs to be edited, corrected, or updated | **revise-doc** |
| A doc was changed and you need to know what else is now stale | **cascade-check** |
| The store feels cluttered; a doc has many history entries; cascade was wide; periodic maintenance | **garden** |
| You want a structural integrity report (no fixes) | **validate** |
| `kb/02-docs/.index/` may be stale after bulk changes | **reindex** |

### apply-to-docs

Run this before acting on any request or plan that should be durably recorded. It:
1. Archives the request as a raw clipping and a normalized reference doc
2. Extracts key concepts and maps them to existing docs
3. Walks the blast radius across the graph (read-only pass first)
4. Warns if the blast radius is large and pauses for confirmation
5. Batch-synthesizes all changes in one coherent pass

Do not skip Step 3 (blast-radius walk) or interleave reads and writes.

### ingest-reference

Gate 2 of the inbox pipeline. Run this on a raw item in `kb/01-raw/` to decompose it into atomic docs. Decomposition is mandatory — a blob ingested as a single doc is a liability. The skill:
1. Creates the raw clipping (in `kb/01-raw/`) and a normalized reference doc (in `kb/02-docs/`)
2. Extracts a typed concept list from the material
3. Runs a conflict-detection pass against existing docs before writing anything
4. Creates or updates docs in one batch pass; runs cascade-check from any corrected existing docs

Never run this on an inbox item directly — promote it to raw first (`ldoc promote`).

### revise-doc

Use for any targeted edit to an existing doc. It:
1. Loads and articulates the current state and intended change
2. Runs a dedup/conflict scan against neighbors and same-type docs
3. Classifies the change (substantive vs. provenance-only)
4. For substantive changes: appends a history entry and runs cascade-check
5. Validates the store after all writes

**Provenance-only changes** (`provenance` or `relates` edges only) do not cascade and may not need a history entry (backfilling initial provenance is not history-worthy; adding a new reference later is).

### cascade-check

Run after any substantive doc change. Two strict passes:

- **Pass 1 (read-only)**: walk the full graph via `ldoc neighbors` and collect verdicts for every reachable node. No writes.
- **Pass 2 (batch write)**: apply all `cascade` verdicts in one coherent pass.

Never interleave reads and writes. Frozen docs (`status: deprecated` or `status: reference`) are never rewritten to track new state — if they conflict, surface as `incompatible`.

When cascade-check is invoked from within another skill (ingest-reference, revise-doc, garden, apply-to-docs), it is a **nested invocation** and must NOT emit its own review summary. The outer skill owns the single episode summary.

### garden

Run on a schedule or when triggered by a wide-cascade warning. Key passes:

- **single-responsibility**: find docs that change for more than one reason and propose concrete splits
- **staleness**: surface docs whose dependencies were updated more recently than the doc itself
- **consistency**: orphan detection + broken edges + missing fields (proposes fixes; `validate` only reports)
- **field-aliases**: normalize stale field names and enum values
- **index-moc**: keep index docs healthy — check for oversized indexes, stale rollups, and orphaned children

Garden always proposes before applying; it never silently rewrites meaning.

---

## Schema rules an agent must respect

### Required fields

Every doc in `kb/02-docs/` must have: `id`, `title`, `label`, `type`, `status`, `level`, `created`.

### Three descriptors

| Field | Format | Role |
|-------|--------|------|
| `label` | Title Case, 2–5 words | Short identifier; used by ldoc for ref resolution |
| `title` | Sentence-length phrase | The authoritative human name of the concept |
| `summary` | 1–3 sentences, ≤ ~50 words | Tight overview mirroring the doc's opening; surfaced verbatim in reviews/search/index maps |

**Summary convention:** keep it to 1–3 sentences (≤ ~50 words) — the gist a reader needs to decide whether to open the doc, written like the doc's opening statement (its Decision/Statement/Context), not a recap of the whole doc. No run-on sentences (cramming everything into one long sentence is not "fewer sentences"). It is shown verbatim in review snapshots, search results, and index maps, so it must stay scannable. When the doc's opening is already tight, the summary can essentially be that opening, lightly condensed.

### Canonical field order

Fields must appear in this order in the frontmatter:

```
id, title, label, summary, type, status, level,
belongs_to, requires, relates, provenance, superseded_by,
domain, scope, created, history
```

`reference` type docs additionally carry `kind`, `source`, `imported` after `history`.

### Valid enum values

```
type:   type | principle | goal | decision | constraint | requirement |
        use-case | guide | component | reference | index
status: living | target | deprecated | reference
level:  incidental | trial | preference | requirement
```

The old `state: actual|target` field is removed from the schema. If encountered, fold `state: target` into `status: target` and drop the `state` key.

### Omit empty fields

**Empty edge lists, empty `history`, empty `domain`, and empty `scope` are omitted from the file entirely.** Do not write `[]`. Absence equals empty — the tooling treats them identically.

### `id` is the filename

The `id` field must match the filename stem exactly (a 14-digit UTC timestamp). Never change `id`. Never rename files — the ID is opaque and permanent.

---

## Edge rules

| Edge | Cascade | Use when |
|------|---------|----------|
| `requires` | hard | This doc is existentially dependent on the target — meaningless or wrong without it |
| `belongs_to` | hard | This doc is structurally a child of the target (index membership, part-of) |
| `relates` | soft / nav | Symmetric clustering / see-also; topic kinship but not a dependency |
| `provenance` | soft / nav | "Was derived from / informed by"; may point at `kb/01-raw/` (raw ids are not graph nodes) |
| `superseded_by` | — | Required when `status: deprecated`; points at the replacement doc(s) |

**Do not point `requires` at a raw file** (`kb/01-raw/<id>.md`). Raw files are not graph nodes. Use `provenance` for that relationship, or `--source` on a reference doc.

**Reverse edges** (`dependents`, `provenance_of`) are generated by `reindex`. Never hand-author them.

**Edge validation**: `ldoc new` and `ldoc link` validate that all specified edge refs resolve before writing. An unresolved ref is an error.

---

## History rules

- `history` is a **change-trail**, not a log of all activity.
- **Never add a creation entry.** The `created` field records when the doc was made; no history entry is needed.
- Append a history entry only when substantive content changes (title, body, type, level, status, requires, belongs_to, tags). Provenance-only changes (adding a `provenance` or `relates` edge) may or may not get an entry depending on intent — backfilling initial provenance is not history-worthy.
- Use `ldoc history <ref> --add "<description>"` — never edit history entries directly.
- Existing history entries are immutable. Append only; never alter or delete prior entries.
- A long history list on a doc is a "hot file" signal: consider running `garden single-responsibility`.

---

## Inbox pipeline: capture vs ingest

Two distinct operations with very different cadences:

**Capture** (gate 0 — instant): use `ldoc inbox add` for anything you want to preserve without stopping to process. No frontmatter, no thinking required.

```bash
echo "rough idea" | ldoc inbox add --body - --title "Rough idea" --source "meeting 2026-06-18"
ldoc inbox add --from-file notes.txt --title "Meeting notes"
ldoc inbox list         # see what's waiting
```

**Accept** (gate 1 — deliberate): when you're ready to process an inbox item, promote it to raw:

```bash
ldoc promote <inbox-id>   # single item
ldoc promote --all        # drain the inbox
```

**Ingest** (gate 2 — the decomposition step): run the `ingest-reference` skill on the promoted raw item. This is where atomicity is produced. It cannot be automated or skipped.

If `ldoc promote <ref>` tells you the item is already in `kb/01-raw/`, it will print guidance to run `/ingest-reference` — that is gate 2.

---

## Deprecation protocol

Deprecating a doc is a two-part mandatory operation. A bare `--status deprecated` is invalid.

```bash
# 1. Add a ## Correction section to the doc body explaining WHY it is wrong
#    and which doc supersedes it. (Use direct file edit or ldoc set --body -)

# 2. Set the superseded_by edge and status
ldoc link <id> --superseded-by <replacement-id>
ldoc set <id> --status deprecated

# 3. Append a history entry
ldoc history <id> --add "deprecated — superseded by <replacement-id>: <one-line reason>"
```

Both the `superseded_by` edge and the `## Correction` section are required. `validate` will flag a deprecated doc with no `superseded_by` edge as an error.

After deprecation, run `cascade-check` from the deprecated doc: all `requires`/`belongs_to` dependents need to know their upstream is now deprecated.

---

## Validate and reindex checkpoints

### When to validate

Run `ldoc validate` (or the `validate` skill):

- After any batch of mutations
- Before finalizing a set of changes
- After any `garden` pass
- Any time you want confidence the store is structurally sound

Address all ERRORs before continuing. Surface WARNINGs to the user for review.

### When to reindex

Run `ldoc reindex` (or the `reindex` skill):

- After bulk doc creation or deletion
- After any doc type changes from or to `index`
- After restructuring `belongs_to` edges
- Before reading `kb/02-docs/.index/hierarchy.md` or `orphans.txt` if they may be stale

Reindex is always idempotent. The `.index/` artifacts are safe to commit.

**Important**: `cascade-check` always calls `ldoc neighbors` for fresh live data — do not read `dependents.json` directly as a substitute for `ldoc neighbors`.

---

## Review summaries

Each skill episode produces exactly one review summary via `ldoc review new --since "$START"`. Reviews are:

- **Post-hoc**: generated after all changes are applied, never before
- **Non-gating**: they record the episode for later signoff; they never block the change
- **One per episode**: nested skill invocations (cascade-check called from within ingest-reference, revise-doc, garden, or apply-to-docs) do NOT emit their own summary — the outer skill owns it

Sign off a review: `ldoc review sign <id> --as "Your Name"`

List unsigned reviews: `ldoc review list --unsigned-by "Your Name"`
