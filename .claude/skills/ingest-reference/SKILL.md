---
name: ingest-reference
description: >
  Bring external material into the live_docs store without creating non-atomic
  blobs. Accepts a file path, pasted text, a chat-session summary, a URL's
  fetched content, or any other raw input. The skill creates a raw clipping doc,
  a normalized summary doc, then — the critical step — decomposes the material
  into single-responsibility docs (principles, decisions, constraints, etc.) or
  links it as supporting evidence to existing docs. Use whenever ingesting
  external knowledge: meeting notes, research, specs, prior-art findings,
  conversations, blog posts, RFCs, or any reference you want to make durable.
---

# ingest-reference — Bring external material into the store atomically (orchestrator)

**Where input comes from (two-gate inbox pipeline):**

- **Gate 0 — capture (drop-point):** Raw material arrives via `ldoc inbox add`
  (or is pasted directly). The inbox (`kb/00-inbox/`) is instant, no-processing.
- **Gate 1 — accept (promote):** A human runs `ldoc promote <id>` to move the
  item from inbox → `kb/01-raw/` with raw-clipping frontmatter. This marks it as
  officially accepted for ingestion.
- **Gate 2 — ingest (this skill):** `ingest-reference` is invoked on a raw item
  in `kb/01-raw/`. This is the decomposition step — it MUST NOT be skipped.
  Running the skill on an inbox item directly (bypassing gate 1) is wrong; promote
  it first.

The cardinal rule: **the decomposition step is where atomicity is produced.**
A raw blob ingested as a single doc is a liability, not an asset. Do not skip
decomposition.

This skill is a **thin orchestrator**. Its unique parts are the raw-clipping +
normalized-summary creation and the two-gate framing above; the decomposition
itself is composed from three sub-skills it invokes in order —
`identify-key-concepts`, `map-concepts-to-docs`, `synthesize-doc-changes` —
keeping ingest's own knobs (unbounded concept extraction + the splitting test).

**Gate 1.5 runs first.** Before any comprehension, this skill invokes
`shard-clipping` (Step 2.5) on the raw. Its sole trigger is concept **volume**, so
for almost everything — including dense, multi-subject design notes — it is a
near-no-op pass-through. Only a genuinely high-volume clipping (more concepts than
one pass can synthesize — a 10k-line mega-doc) gets sharded: `shard-clipping`
gathers its verbatim passages into child raws left **pending** in the raw tier,
and this episode then **ends** — it does not ingest or even enumerate the
children. They are ingested later as their own gate-2 episodes by the backlog loop
over `ldoc raw list --pending`. So one agent context never holds the comprehension
*and* synthesis of an over-large document at once.
That is how `shard-clipping` is reached: you never run it manually; ingest always
passes through it.

---

## You are the orchestrator — run every step through to Step 8

You run this skill from Step 0 to Step 8. Each sub-skill it names
(`/identify-key-concepts`, `/map-concepts-to-docs`, …) runs **inline, in this
same turn**, and its result feeds the step after it — running a sub-skill is
never where you stop. A raw whose concepts were extracted but no docs written is
not "partly ingested"; it is *not ingested*.

- ingest-reference owns the episode — it opens the session (Step 0) and closes it
  into the **one** review for the whole episode (Step 8).
- The sub-skills — `/shard-clipping` (2.5), `/identify-key-concepts` (4),
  `/map-concepts-to-docs` (5a), `/synthesize-doc-changes` (5b), `/cascade-check`
  (6) — each do their one job and leave the result in context; none opens or
  closes a session (no `session start`/`session close`) — episode ownership,
  opening the session and closing it into one review, belongs to this skill alone.
- **Exception — the shard branch.** If `shard-clipping` splits the raw, this
  episode created only the child raws (via the nested shard-clipping) and
  decomposes nothing itself; it then **ends**, leaving the children pending. It
  does NOT ingest or enumerate them. Each child is ingested later by its own
  fresh, separate `ingest-reference` episode (driven by the backlog loop), owning
  its own review. This episode's one Step 8 review covers only the child-raw
  creation.

---

## Step 0 — Open the editing session

```bash
export LDOC_SESSION=$(ldoc session start)
```

Read and apply `.claude/skills/_shared/session-lifecycle.md`. This session mints
the single review summary when it is closed at the end of the episode.

---

## Step 1 — Receive the material

Accept input in any of these forms:

- **File path**: read the file content.
- **Pasted text**: use as-is.
- **URL content**: use the fetched text (the caller is responsible for fetching;
  this skill works with the text only).
- **Chat session / conversation summary**: the caller pastes the summary.

Determine the `source` field value: URL, filename, meeting name/date, person,
or "pasted". If the source is ambiguous, ask before proceeding.

---

## Step 2 — Create the RAW reference doc (immutable clipping)

```bash
ldoc ingest-raw \
  --from-file <path>           # OR: --body "<raw content>" OR: --body -
  --source "<where it came from>" \
  --title "Clipping: <descriptive title>" \  # optional but recommended
  --origin "<corpus/system>" \               # optional: notion, codebase:foo, …
  --medium "<medium>" \                       # optional: pdf, scan, notion-page, …
  --authored-at "<when source written>"       # optional, may be fuzzy: 2024-03, circa 2023
```

When ingesting a raw item that was already promoted from the inbox (gate 1), it
already carries `origin` / `medium` / `authored_at` / `captured` in its frontmatter
— prefer reading those off the raw clipping rather than re-supplying them.

This writes to the **raw/ tier** (repo root `/raw/<id>.md`), NOT to `docs/`.
`raw/` is outside the graph — `livedocs`, `validate`, and `reindex` scan only
`docs/` and will never load raw files.

- `raw/<RAW_ID>.md` is the **immutable archival original**.  Never edit its
  body after creation.
- If the content is large (> ~2000 words), you may truncate it in the raw file
  and note "full content at <source>" in the body — but prefer the full text.
- Note the created id printed to stdout: call it **RAW_ID**.

---

## Step 2.5 — Shard check (run `shard-clipping`) — gate 1.5

Before any comprehension, run **`/shard-clipping`** on `RAW_ID`. It returns one
verdict:

- **`pass-through`** (the common case — clipping fits one pass, ≲50 concepts):
  continue to Step 3 with the single `RAW_ID`. This is a near-no-op; proceed
  exactly as normal.

- **`shard`** (high-volume — over the ~50-concept floor): `shard-clipping` has
  gathered `RAW_ID`'s verbatim passages into pending child raws (each carrying `parent_raw` → `RAW_ID`,
  inherited provenance, and `shard_depth`). Do **NOT** run Steps 3–7 on `RAW_ID`,
  and do **NOT** enumerate or read the children — pulling their text into this
  context would re-accumulate the bulk sharding exists to shed. This episode is
  essentially done:

  1. Leave the children as **pending** raws. They are picked up by whatever
     iterates pending raws (`ldoc raw list --pending` — the backlog loop, or a
     later ingest invocation). Each becomes its own independent gate-2 episode;
     **order does not matter** — duplicate concepts across shards are reconciled by
     `map-concepts-to-docs`' concept-matching and the gardening passes.
  2. Do **NOT** `ldoc raw mark-ingested` the parent — once its children are
     ingested it derives as `[sharded]`; until then it shows `[sharding]`.
  3. Go to Step 8 and emit this episode's single review (covering the child-raw
     creation). Report the verdict and the child ids `shard-clipping` returned (a
     one-line list is fine — just don't read their bodies).

  *Optional single-step continuation:* to make forward progress in this one
  invocation instead of stopping cold, you MAY tail-process **only the first**
  pending child by invoking `ingest-reference` on that single id, leaving the rest
  pending. Never loop over the whole list.

The parent `RAW_ID` is the immutable whole-archive; sharding only adds child raws
beside it.

---

## Step 3 — Create the NORMALIZED reference doc

Read the raw content and produce a cleaned, summarized, lightly structured
version: remove cruft, organize into sections if helpful, extract the core ideas.

Determine `kind`:
- `plan` — if the material is a proposal, roadmap, or action plan.
- `brainstorm` — if it's exploratory, unresolved, or generative.
- `external` — if it's an external spec, RFC, article, or third-party source.
- `clipping` — only if none of the above fit.

Read and apply `.claude/skills/_shared/label-title-summary.md` — `--label` is required and must name the subject (not a fragment); `--title` is optional.

```bash
ldoc new \
  --type reference \
  --kind <kind> \
  --status reference \
  --level incidental \
  --label "<2–5 word Title-Case handle>" \
  --title "<descriptive title>" \  # optional; no "Reference:" prefix — the type is shown automatically on display
  --source "raw/<RAW_ID>.md" \
  --origin "<corpus/system>" \      # carry from the raw clipping if present
  --medium "<medium>" \             # carry from the raw clipping if present
  --authored-at "<when written>" \  # carry from the raw clipping if present
  --body "<normalized summary>"
```

Key differences from Step 2:

- This doc goes into **`docs/`** — it IS a graph node (NORM_ID lives in docs/).
- `--source "raw/<RAW_ID>.md"` is the provenance link to the raw tier.  Use a
  path, not a requires edge — raw files are not graph nodes, so a requires
  entry pointing at RAW_ID would be a dangling edge.
- Do NOT pass `--requires "<RAW_ID>"`.  RAW_ID is not in the graph.
- **Carry provenance forward**: read `origin` / `medium` / `authored_at` off the
  raw clipping (gate-1 promotion preserves them) and pass them here so the graph
  node — and every doc that takes `--provenance <NORM_ID>` — retains
  source-corpus, medium, and source-age context for staleness reasoning.
- `type: reference` docs always get `status: reference` — they are frozen
  supporting material, not truth claims that evolve.

Note the created id: call it **NORM_ID**. This is the provenance anchor handed
to `synthesize-doc-changes` in Step 5; every extracted doc gets
`--provenance <NORM_ID>`.

---

## Step 4 — Extract the concept list (invoke `identify-key-concepts`)

Run — but do not stop after — **`/identify-key-concepts`** on the normalized
reference from Step 3, then carry its concept list into Step 5. Pass ingest's
knobs:

> Extract every distinct durable concept the material asserts (a dense document
> may yield dozens; concepts are often presupposed rather than stated outright).
> Label each `Concept`. **Then apply the splitting test** to each concept already
> found: "This doc changes when ___." If that blank covers more than one concern,
> split the concept in two.

It returns the typed concept list (`Concept / Type / Asserts`) in context — the
input to Step 5.

---

## Step 5 — Decompose into atomic docs (THE KEY STEP)

Decomposition is the two-pass survey-then-write that produces atomicity. It is
composed from two sub-skills; never interleave their reads and writes.

### Step 5a — Survey (run `/map-concepts-to-docs`)

Run — but do not stop after — **`/map-concepts-to-docs`** with the concept list
from Step 4, then carry its verdict map into Step 5b. Emphasis: a full conflict
scan — for every concept, does its claim conflict with something already in
live_docs? It returns the relationship verdict map (`compatible` /
`partial-supersession` / `full-supersession` / `conflict-unresolved`) with a
planned action per concept. (Read-only.)

**Correcting stale existing docs is the primary output — more valuable than any
newly created doc**, because existing docs have dependents and cascade-check will
propagate the correction; freshly created docs have no dependents yet.

**Heed the re-ingestion flag.** `map-concepts-to-docs` now detects when a high
fraction of this source's concepts all map to a single existing normalized / NORM
reference doc — the signal that this source is a **re-ingestion of
already-ingested material** (not new knowledge). When that flag fires, do NOT let
Step 5b mint a fresh duplicate NORM doc and a parallel set of extracted docs.
Instead route to **revise / reconcile**: update the existing NORM doc and its
already-extracted children in place (per `/revise-doc` discipline), folding in
only what genuinely changed since the prior ingest. Treat the prior NORM doc as
the canonical anchor rather than creating a second one beside it.

### Step 5b — Write (run `/synthesize-doc-changes`)

Run **`/synthesize-doc-changes`**, handing it:

- the conflict map from Step 5a (each existing doc with its verdict / planned
  action — revise, deprecate, link-provenance),
- the concept list from Step 4 (for new-doc creation),
- the provenance anchor **NORM_ID** (every extracted doc gets
  `--provenance <NORM_ID>`; duplicated/strengthened concepts link NORM_ID to an
  existing doc's `provenance` instead of creating a new doc).

It applies all changes in one batch: revise/deprecate stale existing docs, create
new atomic docs for unmatched concepts. It returns the list of writes performed.

### Status inference — classify by INTENT, never inherit it from source prose

As `synthesize-doc-changes` assigns each *new* extracted doc its `status`, do not
let it default everything to `living`, and do **not** inherit status from
celebratory source language. A plan that says "done / all todos complete!" is
recording intent at the moment it was written, not the current state of the
system — cheap-model ingestion that stamped plan/design docs `living` wholesale
off such prose is the root cause of stale-cluster drift. Classify each concept's
status by what the material **is**:

- A **plan of future work**, an aspiration, or something proposed-but-not-yet-in-
  force → `status: target` (intended, not yet in force).
- A **statement of in-force design / current reality** — the architecture or
  decision the system is currently built around (or currently intends to be built
  around) → `status: living`.

The discriminator is **intent: plan-of-work vs in-force-design — NOT whether code
corroborates the claim.** Docs capture the *why* (decisions, rationale,
constraints, use-cases), not the *what* the code already encodes — docs lead,
code aligns: an in-force design doc is `living` even when the code
hasn't caught up yet — implementation lag is the only thing separating it from a
fully realized doc. So do not gate `living` on code-presence; doing so would
wrongly pin every brand-new design doc at `target`. When intent is genuinely
ambiguous, prefer `target` and surface the doc for human confirmation rather than
defaulting to `living`.

---

## Step 6 — Cascade from corrected docs (run `/cascade-check`)

After Step 5b corrects or deprecates existing docs, run **`/cascade-check`** from
**those corrected/deprecated docs** (not from freshly created docs — new docs
have no dependents and surface nothing when cascaded from), then continue to
Step 7. (This ingest episode owns the single review summary — Step 8 — so
cascade-check does not emit its own.)

---

## Step 7 — Provenance rule check

After decomposition, every extracted doc MUST have at least one `provenance` entry
pointing to NORM_ID (or directly to the source if there's no normalized layer). A
floating extracted doc with neither `provenance` nor `source` nor `requires` is a
provenance violation — add the `provenance` edge. Then validate:

```bash
ldoc validate
```

---

## Step 7b — Mark the raw item ingested

Once decomposition is complete and validated, flag the RAW item so the backlog
view (`ldoc raw list --pending`) no longer surfaces it:

```bash
ldoc raw mark-ingested <RAW_ID>
```

(Only on the normal / `pass-through` path, where this episode actually
decomposed `RAW_ID`. In the **shard branch** you reach Step 8 without this — the
parent is never marked directly; each child episode marks its own child raw, and
the parent derives as `[sharded]`.)

This writes an `ingested_at` lifecycle field to the raw clipping's frontmatter
(the raw BODY stays immutable). Ingest-state is **hybrid**: this explicit flag is
cross-checked against graph evidence (a NORM doc whose `source`/`provenance`
points at the raw id), so `ldoc raw list` can flag drift if the two disagree —
e.g. an interrupted ingest that wrote docs but never got flagged.

---

## Step 8 — Report and review summary (FINAL step)

After all docs are created and cascades resolved, print a summary:

```
ingest-reference — complete
Source: <source description>
RAW_ID:  <id>   raw/<id>.md   — verbatim, immutable (NOT in graph)
NORM_ID: <id>   docs/<id>.md  — normalized reference (graph node)

Extracted docs:
  <id>  type: principle   title: "<title>"
  <id>  type: decision    title: "<title>"

Corrected existing docs (primary outputs):
  <id>  "<existing doc title>" — revised: <one-line summary of what changed>
  <id>  "<existing doc title>" — deprecated: added Correction section + superseded_by

Linked to existing docs (provenance only):
  <id>  "<existing doc title>" — added <NORM_ID> to provenance
```

Then close the session, minting the single review for the entire ingest episode.
ingest-reference owns it (the nested sub-skills never open or close one):

```bash
ldoc session close --summary "<one-line agent recap of the episode>"
```

The review is built from the session's change log; confirm `touched` reflects the
episode's changes. Report the returned review id:

```
Review summary created: <id>   (reviews/<id>.md)
```

Review is **post-hoc and non-gating**: it records the ingest episode for later
signoff and never blocks the change. Reviewers inspect it via
`ldoc review show <id>`.

---

## Atomicity checklist before finishing

- [ ] Every extracted doc has exactly one responsibility (single-reason-to-change test).
- [ ] Every extracted doc has provenance: `provenance` includes NORM_ID (not RAW_ID — raw is not a graph node).
- [ ] `raw/<RAW_ID>.md` body is the verbatim, unedited original (raw tier, outside docs/).
- [ ] NORM_ID lives in `docs/` with `source: "raw/<RAW_ID>.md"` pointing back to the raw tier, and `status: reference`.
- [ ] NORM_ID body is a cleaned summary, not the extraction outputs.
- [ ] `identify-key-concepts` (Step 4) ran with the splitting test before any KB query — every concept has a type and an Asserts sentence.
- [ ] `map-concepts-to-docs` conflict scan (Step 5a) ran before any write.
- [ ] Any corrected or deprecated existing docs have a `## Correction` section and, if deprecated, a `superseded_by` edge.
- [ ] cascade-check was run from CORRECTED EXISTING docs (not from freshly created docs).
- [ ] Extracted doc bodies describe the decision/mental model, not implementation history or absence. Gap between model and reality is expressed via `status: target`, not body text.
- [ ] No extracted doc duplicates an existing doc.
- [ ] No `requires` edge points at RAW_ID — raw files are not graph nodes.
