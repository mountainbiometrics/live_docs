---
name: apply-to-docs
description: >
  Run a request or plan against the live_docs knowledge base before acting on
  it: extract key concepts, map them to existing docs, walk the full impact
  graph to identify the blast radius, pause only for unresolved conflicts or
  unintended side-effects (not merely because many docs will change), then
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
own request-archival and restate steps, and its pause-for-conflicts /
unintended-side-effects gate.

---

## You are the orchestrator — run every step through to Step 9

You run this skill through to Step 9 (the review summary). Each sub-skill it
names (`/identify-key-concepts`, `/map-concepts-to-docs`, …) runs **inline, in
this same turn**, and its result feeds the step after it — running a sub-skill is
never where you stop.

- apply-to-docs owns the episode — it opens the session and closes it into the
  **one** review for the whole episode (Step 9).
- The sub-skills each do their one job and leave the result in context; none
  opens or closes a session (no `session start`/`session close`) — episode
  ownership, opening the session and closing it into one review, belongs to this
  skill alone.

---

## Step 0 — Open the editing session

```bash
export LDOC_SESSION=$(ldoc session start)
```

Read and apply `.claude/skills/_shared/session-lifecycle.md`.

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

Archive the input now, before any concept extraction, so all new docs can point
back to an immutable provenance target. Prefer the **verbatim** user text when
that is what arrived; if you are archiving an agent restatement or a mixed
session digest, say so honestly in `--source`.

```bash
ldoc ingest-raw \
  --body "<verbatim request text>" \
  --source "<accurate origin: user-request | working-session <date/desc> | agent restatement of …>" \
  --title "Clipping: <short description of the request>"
```

Use `--source "user-request"` only when the body is the user's words (or a
faithful paste). Ratification of an idea is not authorship of the wording.

Note the returned id: call it **RAW_ID**. This goes to `raw/` — outside the
graph — and is the immutable original.

Then create a normalized reference doc summarizing the request's intent. Read and apply `.claude/skills/_shared/label-title-summary.md` — `--label` is required and must name the subject (not a fragment); `--title` is optional.

```bash
ldoc new \
  --type reference \
  --kind plan \
  --status reference \
  --level incidental \
  --label "<2–5 word Title-Case handle>" \
  --title "<short description>" \   # optional; no "Reference:" prefix — the type is shown automatically on display
  --source "raw/<RAW_ID>.md" \
  --body "<the one-paragraph restatement from Step 1>"
```

Note the returned id: call it **REQ_ID**. This is the provenance anchor handed
to `synthesize-doc-changes` in Step 6; every new doc will carry
`--provenance <REQ_ID>`.

---

## Step 2 — Extract concepts (invoke `identify-key-concepts`)

Run — but do not stop after — **`/identify-key-concepts`** on the normalized
restatement from Step 1, then carry its concept list into Step 3:

> Extract every distinct durable concept the request asserts, labeled `Concept`.
> Root-over-decision applies (identify-key-concepts invariant): prefer
> first-class why-roots over a decision inventory. (No splitting test.)

It returns a typed concept list (`Concept / Type / Asserts`) in context — the
input to Step 3.

---

## Step 3 — Map concepts to existing docs (run `/map-concepts-to-docs`)

Run — but do not stop after — **`/map-concepts-to-docs`** with the concept list
from Step 2, then carry its verdict map into Step 4. Emphasis: full concept
survey across the store. It returns a relationship verdict map (`compatible` /
`partial-supersession` / `full-supersession` / `conflict-unresolved`) in context.
(Read-only.)

---

## Step 4 — Assess the blast radius (run `/assess-blast-radius`)

Run — but do not stop after — **`/assess-blast-radius`** from every
non-`compatible` match in the Step 3 map, passing the restatement as the change
description, then evaluate the pause gate in Step 5. It walks the graph and
returns the **complete impact set** with verdicts (`cascade-extend` /
`cascade-full` / `conflict-unresolved` / `inconsequential`) and the frozen-doc
rule applied. (Read-only.)

---

## Step 5 — Pause gate: conflicts and unintended side-effects

This pause is apply-to-docs's own discipline. The blast-radius survey (Steps 3–4)
always runs — it informs a coherent synthesis. The pause is **not** a
permission-slip for doing the work the user asked for.

**Pause when (and only when) either holds:**

1. **Invariant — unresolved conflicts.** Any `conflict-unresolved` docs are
   present (frozen/deprecated clash, or a contradiction the synthesis cannot
   mechanically reconcile). The user must address something the conversation
   has not settled yet.
2. **Judgment — unintended side-effects.** The impact set reaches docs or
   deprecations that look *outside* what the request implies — e.g. full
   supersession of a living doc the request never touched, or cascade into an
   unrelated cluster. Weigh: is this the coherent consequence of the stated
   intent, or a surprise the user has not had a chance to catch? Large counts
   of `partial-supersession` / `cascade-extend` on docs that clearly belong to
   the request are **not** a pause reason by themselves.

**Do not pause** solely because many docs will change, or because the impact
set is "large." That rubber-stamps expected work and trains the user to type
"yes" without reading.

If pausing, **stop and present before writing anything:**

```
⚠  apply-to-docs: pause — <conflicts | unintended side-effects | both>

Why this is not just "proceeding with your request":
  <one or two sentences: what is unresolved or surprising>

conflict-unresolved (if any):
  <id>  "<title>"
      Conflict: <one sentence describing the incompatibility>

Surprising / out-of-scope impact (if any):
  <id>  "<title>"  verdict: <…>  — <why this looks unintended>

Expected impact (informational, not a gate): N docs will be revised/created
as the coherent consequence of the request.

Continue? (yes / no / resolve conflicts first)
```

Do not proceed until the user confirms. If they say "resolve conflicts first",
address those docs via clarifying questions before continuing. If "no", exit
with no further writes (archival from Step 1b may already exist — leave it).

If neither trigger holds, proceed directly to Step 6 — even when the expected
impact set is large.

---

## Step 6 — Batch-synthesize all changes (run `/synthesize-doc-changes`)

Run **`/synthesize-doc-changes`** — never raw `ldoc new`/`set` in its place, as
it is the only place the store's write-time discipline is reachable (label
shape, `domain` vs `scope`, body style, placement). Hand it:

- the complete impact set from Step 4 (each affected doc with its verdict),
- the concept list from Step 2 (for new-doc creation),
- the provenance anchor **REQ_ID** (every new doc gets `--provenance <REQ_ID>`).

It writes deprecations → revisions → new docs in one coherent batch, upstream →
downstream, and returns the list of writes performed in context for the report.

---

## Step 7 — Validate the store

After all writes, confirm structural soundness:

```bash
ldoc validate
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

## Step 9 — Close the session (FINAL step)

**Batch self-check (before close).** Spot-check the writes against the archived
request — process smells, not a truth oracle:

- **Type mix:** mostly `decision` docs restating outcomes, with why only in
  body prose → revisit before closing.
- **Labels:** new handles absent from the request's vocabulary → rename or flag.
- **Levels:** unconfirmed agent articulations must not ship as
  `level: requirement` merely because they carry `--provenance <REQ_ID>`.
- **Source string:** agent-authored archive bodies must not claim `user-request`.
- **Status:** any new `status: target` without explicit deferral (weeks+/migration/
  external deps) in the request → flip to `living` or justify per
  `.claude/skills/_shared/status-living-vs-target.md`. Principles/constraints/goals/requirements
  born `target` are almost always wrong.

apply-to-docs owns the episode: close the session, which mints the single review
over everything the episode touched (the nested sub-skills never open or close
one):

```bash
ldoc session close --summary "<one-line agent recap of the episode>"
```

The review is built from the session's change log — it auto-classifies
Additions/Revisions and populates `touched` from what actually changed. Report the
review id to the user:

```
Review summary created: <id>   (reviews/<id>.md)
Self-check: <type-mix / labels / levels / source / status — ok or what you fixed>
```

Review is **post-hoc and non-gating** (see `review-is-post-hoc`): this records
the episode for later signoff and never blocks the apply.

---

## Body-content rule (store-wide convention)

Doc bodies describe the decision or mental model — what is true (or intended)
and why. They do NOT narrate implementation state, absence, or history. Status
assignment (`living` vs `target`) follows
`.claude/skills/_shared/status-living-vs-target.md` — default `living`;
`target` only for explicitly deferred realization, not because this skill runs
before current-work implementation. Also apply
`.claude/skills/_shared/cruft-verdicts.md`'s detection lens proactively.
(Enforced by `synthesize-doc-changes`, restated here as the store-wide
convention.)
