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

# ingest-reference — Bring external material into the store atomically

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

---

## Step 0 — Capture the episode start time

Before doing anything else, record the current UTC time:

```bash
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

This timestamp will be used at the end of the episode to generate a single
review summary covering all docs created during the ingest.

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

Note the created id: call it **NORM_ID**.

---

## Step 4 — Extract the concept list (read-only, no KB queries yet)

Read the normalized reference in full. This step produces nothing but a list
— no `ldoc` commands, no KB queries. The list is the input to Step 5.

**Scan by type.** Use the table below as a recognition checklist. For each
category, ask: "Does the material contain an instance of this?" Hunt top-down
through the text for each type in turn before moving on.

| What you find | Type |
|---|---|
| A design truth or rule that should guide future work | `principle` |
| A significant choice with a rationale | `decision` |
| An external force limiting options | `constraint` |
| A must-have behavior or property | `requirement` |
| A user story or workflow | `use-case` |
| A capability description | `component` |

When the material describes **how the system should behave** (a choice among
alternatives with a rationale), prefer `decision` over `principle`. Principles
are universal guidelines; decisions are specific choices.

Name every concept you find — there is no upper limit. A dense document may
yield dozens. Concepts are often presupposed rather than stated outright —
goals, design principles, and requirements may be implied by the text rather
than asserted as explicit claims. If you find yourself with very few, re-read
the material through each type lens again.

For each concept found, write it down as:

```
Concept: "<short noun phrase>"
  Type:    <principle | decision | constraint | requirement | use-case | component>
  Asserts: <one sentence: the single claim this concept makes about how things should be>
```

Commit each `Asserts` sentence before moving to Step 5. A precise claim
produces exact KB matches or confident misses. A vague phrase produces weak
matches that get accepted when they should be rejected.

**Splitting refinement (apply after you have the full list):** For each
concept you've already found, apply the single-sentence test: "This doc
changes when ___." If that blank covers more than one concern, split the
concept into two before proceeding. This is a refinement tool, not a
discovery lens — use it only after the type-scan above is complete.

---

## Step 5 — Decompose into atomic docs (THE KEY STEP)

This step has **two sub-passes**: survey for conflicts first, then write.
Never interleave the two: each write changes the state that subsequent
conflict checks reason about.

### Step 5a — Survey (read-only conflict detection)

For every concept in the pre-distill list, ask: does this claim conflict with
something already in live_docs? The source rarely says "doc 1234 is wrong"
outright — it just asserts a concept that contradicts an existing claim. Search
for docs making the opposing claim:

```bash
python3 scripts/ldoc.py find "<key claim or concept from source>"
```

Also list all docs of the same type to catch anything text search misses:

```bash
python3 scripts/ldoc.py ls --type <type> --json
```

For each matching existing doc, load and read it:

```bash
python3 scripts/ldoc.py show <candidate-id>
```

Judge: is the source's claim compatible, or does it assert something
incompatible with what the doc says?

Build a conflict map across ALL concepts before writing anything:

```
Concept: "<short noun phrase>"
  Asserts: "<new claim>"
  Matches:
    <id>  "<existing title>"  — <compatible | partial-supersession | full-supersession | conflict-unresolved>
      Reason: <one sentence>
  Action planned: <revise | deprecate | link-provenance | create-new>
```

**Correcting stale existing docs is the primary output — more valuable than any
newly created doc**, because existing docs have dependents and cascade-check will
propagate the correction; freshly created docs have no dependents yet and surface
nothing when cascaded from.

### Step 5b — Write (apply all changes in one batch)

With the complete conflict map in hand, apply all changes:

**When the source contradicts an existing doc:**

- If the existing doc is **living or target** (`status: living` or `status: target`):
  revise it to reflect the correct claim. Write the doc as its single correct
  current state — if prior text would now be misleading, rewrite it rather than
  qualifying it. Do not create a new doc that says the same corrected thing —
  update the one that's there.
- If the source **supersedes** the existing doc entirely (the doc's entire claim
  is now wrong): deprecate the existing doc:
  1. Add a `## Correction` section to the body explaining why it is wrong and
     which doc (or this ingest episode's output) supersedes it.
  2. Set `status: deprecated` and add the superseding doc id(s) to `superseded_by`:
     ```bash
     python3 scripts/ldoc.py set <existing-id> --status deprecated
     python3 scripts/ldoc.py link <existing-id> --superseded-by <new-id>
     ```
  3. A bare status flip without a `## Correction` section is invalid — do both.
- After correcting or deprecating existing docs, **run cascade-check from those
  corrected docs** (not from freshly created docs). They have dependents; new
  docs do not.

**Body-content rule.** Extracted doc bodies describe the decision or mental
model — what is true (or intended) and why. Anti-patterns to avoid:
- Narrating absence or implementation state ("X was never built", "a migration
  will happen"). If reality doesn't match the model yet, set `status: target`;
  the body need not say so.
- "Extension" notes that are really migration plans rather than corrections to
  the doc's own claim.

For each concept in the list (from Step 4) that has no existing match, or
whose only matches are frozen/deprecated, create a new doc:

1. Create with `ldoc new`:
   ```bash
   python3 scripts/ldoc.py new \
     --type <type> \
     --title "<precise, single-responsibility title>" \
     --level <incidental|trial|preference|requirement> \
     --status <living|target> \
     --provenance "<NORM_ID>" \
     --tags-scope "<scope tags, e.g. live_docs,sinai>" \
     --body "<the extracted content>"
   ```
   The `--provenance NORM_ID` establishes provenance: this doc was extracted from /
   informed by that reference. This is the **provenance rule**.
   Use `--requires` for genuine existential dependencies (e.g. a decision that is
   meaningless without a principle), or `--belongs-to` for structural parent/child
   membership, added separately when they exist.
3. If the extracted idea DUPLICATES or STRENGTHENS an EXISTING doc: do not create
   a new doc. Instead, link NORM_ID to the existing doc's `provenance` list (not
   `requires`):
   ```bash
   python3 scripts/ldoc.py link <existing-id> --provenance <NORM_ID>
   ```

---

## Step 6 — Provenance rule check

After decomposition, every extracted doc MUST have at least one `provenance` entry
pointing to NORM_ID (or directly to the source if there's no normalized layer). A
floating extracted doc with neither `provenance` nor `source` nor `requires` is a
provenance violation — add the `provenance` edge.

---

## Step 7 — Report

After all docs are created, print a summary:

```
ingest-reference — complete
Source: <source description>
RAW_ID:  <id>   raw/<id>.md   — verbatim, immutable (NOT in graph)
NORM_ID: <id>   docs/<id>.md  — normalized reference (graph node)

Extracted docs:
  <id>  type: principle   title: "<title>"
  <id>  type: decision    title: "<title>"
  <id>  type: constraint  title: "<title>"

Corrected existing docs (primary outputs):
  <id>  "<existing doc title>" — revised: <one-line summary of what changed>
  <id>  "<existing doc title>" — deprecated: added Correction section + superseded_by

Linked to existing docs (provenance only):
  <id>  "<existing doc title>" — added <NORM_ID> to provenance

Next: run cascade-check from each CORRECTED EXISTING doc (not from newly created
docs). Corrected docs have dependents; new docs do not.
```

---

## Step 8 — Generate the review summary (FINAL step)

After all raw/normalized/extracted docs are created and any cascades are
resolved, emit a single review summary for the entire ingest episode.

Review is **post-hoc and non-gating** (see `review-is-post-hoc`): this step
records the episode for later review and signoff. It never blocks the change.

```bash
python3 scripts/ldoc.py review new --since "$START"
```

Report the returned review id to the user:

```
Review summary created: <id>   (reviews/<id>.md)
```

This is the canonical record of the ingest episode. Reviewers can inspect it
via `python3 scripts/ldoc.py review show <id>`.

---

## Atomicity checklist before finishing

- [ ] Every extracted doc has exactly one responsibility (single-reason-to-change test).
- [ ] Every extracted doc has provenance: `provenance` includes NORM_ID (not RAW_ID — raw is not a graph node).
- [ ] `raw/<RAW_ID>.md` body is the verbatim, unedited original (raw tier, outside docs/).
- [ ] NORM_ID lives in `docs/` with `source: "raw/<RAW_ID>.md"` pointing back to the raw tier, and `status: reference`.
- [ ] NORM_ID body is a cleaned summary, not the extraction outputs.
- [ ] Concept list (Step 4) was completed before any KB queries — every concept has a type and an Asserts sentence.
- [ ] Conflict-detection pass was run (Step 5a): `ldoc find` was used for each concept before writing anything.
- [ ] Any corrected or deprecated existing docs have a `## Correction` section and, if deprecated, a `superseded_by` edge.
- [ ] cascade-check was run from CORRECTED EXISTING docs (not from freshly created docs).
- [ ] Extracted doc bodies describe the decision/mental model, not implementation history or absence. Gap between model and reality is expressed via `status: target`, not body text.
- [ ] No extracted doc duplicates an existing doc (checked via `ldoc find` on titles during Step 5a).
- [ ] No `requires` edge points at RAW_ID — raw files are not graph nodes.
