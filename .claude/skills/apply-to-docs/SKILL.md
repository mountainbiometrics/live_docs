---
name: apply-to-docs
description: >
  Run a request or plan against the live_docs knowledge base before acting on
  it: extract key concepts, map them to existing docs, walk the full impact
  graph to identify the blast radius, warn when that radius is large, then
  batch-synthesize a coherent new state for all affected docs in one pass. Use
  whenever a user request or design plan should be durably recorded — the skill
  ensures live_docs converges to the new intent rather than silently drifting
  from it.
---

# apply-to-docs — Land a request or plan into live_docs (orchestrator)

The cardinal rule: **identify the full blast radius before writing a single
byte.** Two passes, cleanly separated:

1. **Identify** — read-only survey of every doc the request touches, including
   cascade neighbors. Produces a complete picture of what will change.
2. **Synthesize** — write all changes in one coherent batch, with the full
   picture in view.

This skill is a **thin orchestrator**. The shared phases live in four sub-skills
it invokes in order — `identify-key-concepts`, `map-concepts-to-docs`,
`assess-blast-radius`, `synthesize-doc-changes` — keeping only apply-to-docs's
own knobs (3–10 concepts), its request-archival and restate steps, and its
pause-before-implementing gate.

---

## This skill OWNS the episode (recursion / duplicate-review discipline)

Exactly like cascade-check's "orchestrator owns the episode" contract:

- apply-to-docs captures the single `START` timestamp and emits the **one**
  review summary for the whole episode (Step 9).
- Every sub-skill it invokes is a **nested invocation**: tell each one so. Nested
  sub-skills must NOT capture their own `START`, must NOT run `ldoc review new`,
  and must NOT re-invoke this orchestrator. They leave their labeled output in
  context for the next step to read.

---

## Step 0 — Capture the episode start time

```bash
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

---

## Step 1 — Receive and normalize the input

Accept the user's request or plan in any of these forms:

- **Inline text** — a request, proposal, or design statement pasted directly.
- **File path** — read the file content.
- **Structured plan** — a numbered list of intended changes / behaviors.

Produce a one-paragraph **plain-language restatement** of what the request
intends: what should be true afterward, what behavior or rule is being
established, what is being changed or discarded. Show this to the user before
proceeding (or proceed silently if the request is unambiguous and short).

When a request is entirely about mechanics ("run validate", "reindex"), there
are no concepts to apply — say so and exit. If the request is clearly
exploratory or hypothetical, run through Steps 2–4 only (present the impact
analysis but skip all writes).

---

## Step 1b — Archive the request as a raw clipping

The user's request is the authoritative provenance source for everything this
skill creates. Archive it now, before any concept extraction, so all new docs
can point back to it.

```bash
python3 scripts/ldoc.py ingest-raw \
  --body "<verbatim request text>" \
  --source "user-request" \
  --title "Clipping: <short description of the request>"
```

Note the returned id: call it **RAW_ID**. This goes to `raw/` — outside the
graph — and is the immutable original.

Then create a normalized reference doc summarizing the request's intent:

```bash
python3 scripts/ldoc.py new \
  --type reference \
  --kind plan \
  --status reference \
  --level incidental \
  --title "Reference: <short description>" \
  --source "raw/<RAW_ID>.md" \
  --body "<the one-paragraph restatement from Step 1>"
```

Note the returned id: call it **REQ_ID**. This is the provenance anchor handed
to `synthesize-doc-changes` in Step 6; every new doc will carry
`--provenance <REQ_ID>`.

---

## Step 2 — Extract concepts (invoke `identify-key-concepts`)

Invoke the **`identify-key-concepts`** skill on the normalized restatement from
Step 1, as a **nested invocation**. Pass apply-to-docs's knob:

> Extract **3–10 key concepts**, labeled `Concept`. (No splitting test.)

It returns a typed concept list (`Concept / Type / Asserts`) in context. Keep it
for Step 3.

---

## Step 3 — Map concepts to existing docs (invoke `map-concepts-to-docs`)

Invoke the **`map-concepts-to-docs`** skill with the concept list from Step 2, as
a **nested invocation**. Emphasis: full concept survey across the store. It
returns a relationship verdict map (`compatible` / `partial-supersession` /
`full-supersession` / `conflict-unresolved`) in context. (Read-only — safe to run
via `context: fork` if the store is large.)

---

## Step 4 — Assess the blast radius (invoke `assess-blast-radius`)

Invoke the **`assess-blast-radius`** skill from every non-`compatible` match in
the Step 3 map, as a **nested invocation**, passing the restatement as the change
description. It walks the graph and returns the **complete impact set** with
verdicts (`cascade-extend` / `cascade-full` / `conflict-unresolved` /
`inconsequential`) and the frozen-doc rule applied. (Read-only — safe to run via
`context: fork` if the graph is large.)

---

## Step 5 — Pause gate: warn if blast radius is large

This pause is apply-to-docs's own discipline (see the **Apply-to-docs Must
Pause** requirement doc). Evaluate the complete impact set from Steps 3–4.

**Trigger this pause if ANY of the following are true:**

- `full-supersession` or `cascade-full` count combined ≥ 2, OR
- All non-`compatible`/`inconsequential` verdicts combined ≥ 4, OR
- Any `conflict-unresolved` docs are present.

If triggered, **stop and present to the user before writing anything:**

```
⚠  apply-to-docs: large impact detected

Your request touches N existing docs:
  full-supersession / cascade-full: N  — these docs will be deprecated entirely
  partial-supersession / cascade-extend: N  — these docs will be revised
  conflict-unresolved: N  — these docs conflict and need your input

Affected docs:
  <id>  "<title>"  verdict: full-supersession
  <id>  "<title>"  verdict: partial-supersession
  <id>  "<title>"  verdict: conflict-unresolved
      Conflict: <one sentence describing the incompatibility>

Continue with these changes? (yes / no / resolve conflicts first)
```

Do not proceed until the user confirms. If the user says "resolve conflicts
first", address the `conflict-unresolved` docs via clarifying questions before
continuing. If the user says "no", exit cleanly with no writes.

If thresholds are not met and there are no unresolved conflicts, proceed
directly to Step 6.

---

## Step 6 — Batch-synthesize all changes (invoke `synthesize-doc-changes`)

Invoke the **`synthesize-doc-changes`** skill, as a **nested invocation**,
handing it:

- the complete impact set from Step 4 (each affected doc with its verdict),
- the concept list from Step 2 (for new-doc creation),
- the provenance anchor **REQ_ID** (every new doc gets `--provenance <REQ_ID>`).

It writes deprecations → revisions → new docs in one coherent batch, upstream →
downstream, and returns the list of writes performed in context for the report.
(This phase runs inline — it needs the whole impact set in view.)

---

## Step 7 — Validate the store

After all writes, confirm structural soundness:

```bash
python3 scripts/ldoc.py validate
```

Address any ERRORs before finishing. Surface WARNINGs to the user for review.

---

## Step 8 — Report

```
apply-to-docs — complete
Request: "<one-line restatement of the intent>"
RAW_ID:  <id>   raw/<id>.md  — verbatim clipping (not in graph)
REQ_ID:  <id>   docs/<id>.md — normalized reference (provenance anchor)

Concepts identified: N
  "<concept>"  type: <type>  →  <action taken>

Docs changed:
  <id>  "<title>"  deprecated  — superseded by <REPLACEMENT_ID>
  <id>  "<title>"  revised     — <one-line: what changed>
  <id>  "<title>"  created     — new doc for concept "<concept>"

Unchanged docs (compatible / inconsequential):
  <id>  "<title>"

Validation: <N docs scanned — clean | N errors, N warnings>
```

---

## Step 9 — Generate the review summary (FINAL step)

apply-to-docs owns the single review summary for the episode (the nested
sub-skills never emit one):

```bash
python3 scripts/ldoc.py review new --since "$START"
```

Report the review id to the user:

```
Review summary created: <id>   (reviews/<id>.md)
```

Review is **post-hoc and non-gating** (see `review-is-post-hoc`): this records
the episode for later signoff and never blocks the apply.

---

## Body-content rule (store-wide convention)

Doc bodies describe the decision or mental model — what is true (or intended)
and why. They do NOT narrate implementation state, absence, or history. If
implementation lags the model, express the gap with `status: target` — the
body need not say so. (Enforced by `synthesize-doc-changes`, restated here as
the store-wide convention.)
