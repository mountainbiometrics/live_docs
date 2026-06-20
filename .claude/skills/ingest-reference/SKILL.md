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

---

## This skill OWNS the episode (recursion / duplicate-review discipline)

Exactly like cascade-check's "orchestrator owns the episode" contract:

- ingest-reference captures the single `START` timestamp (Step 0) and emits the
  **one** review summary for the whole episode (Step 8).
- Every sub-skill it invokes — `identify-key-concepts`, `map-concepts-to-docs`,
  `synthesize-doc-changes`, and `cascade-check` (Step 6) — is a **nested
  invocation**: tell each one so. Nested sub-skills must NOT capture their own
  `START`, must NOT run `ldoc review new`, and must NOT re-invoke this
  orchestrator.

---

## Step 0 — Capture the episode start time

```bash
date -u +%Y-%m-%dT%H:%M:%SZ
```

Record the literal timestamp it prints (e.g. `2026-06-19T23:48:00Z`); you'll paste this exact value into `review new --since` at the end of the episode.

This timestamp generates the single review summary at the end of the episode.

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
python3 scripts/ldoc.py ingest-raw \
  --from-file <path>           # OR: --body "<raw content>" OR: --body -
  --source "<where it came from>" \
  --title "Clipping: <descriptive title>"   # optional but recommended
```

This writes to the **raw/ tier** (repo root `/raw/<id>.md`), NOT to `docs/`.
`raw/` is outside the graph — `livedocs`, `validate`, and `reindex` scan only
`docs/` and will never load raw files.

- `raw/<RAW_ID>.md` is the **immutable archival original**.  Never edit its
  body after creation.
- If the content is large (> ~2000 words), you may truncate it in the raw file
  and note "full content at <source>" in the body — but prefer the full text.
- Note the created id printed to stdout: call it **RAW_ID**.

---

## Step 3 — Create the NORMALIZED reference doc

Read the raw content and produce a cleaned, summarized, lightly structured
version: remove cruft, organize into sections if helpful, extract the core ideas.

Determine `kind`:
- `plan` — if the material is a proposal, roadmap, or action plan.
- `brainstorm` — if it's exploratory, unresolved, or generative.
- `external` — if it's an external spec, RFC, article, or third-party source.
- `clipping` — only if none of the above fit.

```bash
python3 scripts/ldoc.py new \
  --type reference \
  --kind <kind> \
  --status reference \
  --level incidental \
  --title "Reference: <descriptive title>" \
  --source "raw/<RAW_ID>.md" \
  --body "<normalized summary>"
```

Key differences from Step 2:

- This doc goes into **`docs/`** — it IS a graph node (NORM_ID lives in docs/).
- `--source "raw/<RAW_ID>.md"` is the provenance link to the raw tier.  Use a
  path, not a requires edge — raw files are not graph nodes, so a requires
  entry pointing at RAW_ID would be a dangling edge.
- Do NOT pass `--requires "<RAW_ID>"`.  RAW_ID is not in the graph.
- `type: reference` docs always get `status: reference` — they are frozen
  supporting material, not truth claims that evolve.

Note the created id: call it **NORM_ID**. This is the provenance anchor handed
to `synthesize-doc-changes` in Step 5; every extracted doc gets
`--provenance <NORM_ID>`.

---

## Step 4 — Extract the concept list (invoke `identify-key-concepts`)

Invoke the **`identify-key-concepts`** skill on the normalized reference from
Step 3, as a **nested invocation**. Pass ingest's knobs:

> Extract concepts with **no upper limit** (a dense document may yield dozens;
> concepts are often presupposed rather than stated outright). Label each
> `Concept`. **Then apply the splitting test** to each concept already found:
> "This doc changes when ___." If that blank covers more than one concern, split
> the concept in two.

It returns the typed concept list (`Concept / Type / Asserts`) in context. This
list is the input to Step 5.

---

## Step 5 — Decompose into atomic docs (THE KEY STEP)

Decomposition is the two-pass survey-then-write that produces atomicity. It is
composed from two sub-skills; never interleave their reads and writes.

### Step 5a — Survey (invoke `map-concepts-to-docs`)

Invoke the **`map-concepts-to-docs`** skill with the concept list from Step 4,
as a **nested invocation**. Emphasis: a full conflict scan — for every concept,
does its claim conflict with something already in live_docs? It returns the
relationship verdict map (`compatible` / `partial-supersession` /
`full-supersession` / `conflict-unresolved`) with a planned action per concept.
(Read-only — safe to run via `context: fork` if the store is large.)

**Correcting stale existing docs is the primary output — more valuable than any
newly created doc**, because existing docs have dependents and cascade-check will
propagate the correction; freshly created docs have no dependents yet.

### Step 5b — Write (invoke `synthesize-doc-changes`)

Invoke the **`synthesize-doc-changes`** skill, as a **nested invocation**,
handing it:

- the conflict map from Step 5a (each existing doc with its verdict / planned
  action — revise, deprecate, link-provenance),
- the concept list from Step 4 (for new-doc creation),
- the provenance anchor **NORM_ID** (every extracted doc gets
  `--provenance <NORM_ID>`; duplicated/strengthened concepts link NORM_ID to an
  existing doc's `provenance` instead of creating a new doc).

It applies all changes in one batch: revise/deprecate stale existing docs, create
new atomic docs for unmatched concepts. It returns the list of writes performed.

---

## Step 6 — Cascade from corrected docs (invoke `cascade-check`, nested)

After Step 5b corrects or deprecates existing docs, invoke the **`cascade-check`**
skill from **those corrected/deprecated docs** (not from freshly created docs —
new docs have no dependents and surface nothing when cascaded from). Tell
cascade-check this is a **nested invocation** so it does not emit its own review
summary.

---

## Step 7 — Provenance rule check

After decomposition, every extracted doc MUST have at least one `provenance` entry
pointing to NORM_ID (or directly to the source if there's no normalized layer). A
floating extracted doc with neither `provenance` nor `source` nor `requires` is a
provenance violation — add the `provenance` edge. Then validate:

```bash
python3 scripts/ldoc.py validate
```

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

Then emit the single review summary for the entire ingest episode. ingest-
reference owns it (the nested sub-skills never emit one):

```bash
python3 scripts/ldoc.py review new --since "2026-06-19T23:48:00Z"   # ← the literal value you recorded at the start
```

After it runs, confirm `touched` is non-empty and reflects the episode's changes.

Report the returned review id:

```
Review summary created: <id>   (reviews/<id>.md)
```

Review is **post-hoc and non-gating** (see `review-is-post-hoc`): it records the
ingest episode for later signoff and never blocks the change. Reviewers inspect
it via `python3 scripts/ldoc.py review show <id>`.

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
