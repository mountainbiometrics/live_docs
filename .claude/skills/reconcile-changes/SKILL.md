---
name: reconcile-changes
user-invocable: true
description: >
  Catch the docs up to reality. After a working session where decisions were
  made and changes were built but never written down, reconcile-changes ingests
  those already-real decisions into the live_docs store as born-`living` docs.
  Unlike apply-to-docs it does NOT pause before implementing — the change already
  happened, so we record reality rather than propose it. Unlike ingest-reference
  the source is our own session, not external material. The priority is the
  abstract, non-recoverable knowledge — principles, goals, use-cases,
  constraints, and the rationale behind decisions — not implementation facts that
  code and existing docs can re-derive. Use after any session that changed
  reality without updating the KB.
---

# reconcile-changes — Catch the docs up to reality (orchestrator)

The cardinal rule: **record what is already true; do not propose it.** A working
session decided things and built them; the store never heard about it. This skill
walks that gap closed — the resulting docs are born `status: living`, not
`target`, because they describe reality as it now stands.

This skill is a **thin orchestrator**. The shared phases live in sub-skills it
invokes in order — `identify-key-concepts`, `map-concepts-to-docs`,
`assess-blast-radius`, `synthesize-doc-changes`, then `cascade-check` — keeping
only reconcile-changes's own knobs: the optional digest-clipping step, the bias
toward abstract/why knowledge, the heavy-dedup emphasis, and the born-`living`
synthesis knob.

---

## How this differs from apply-to-docs and ingest-reference (read first)

reconcile-changes shares almost all of its machinery with the other two
orchestrators but differs on three load-bearing points. State these explicitly
to yourself before starting:

- **No pre-implementation pause (vs. apply-to-docs).** apply-to-docs deliberately
  pauses and warns before writing, because there the change is a *proposal* the
  user might still reconsider or catch as a mistake (see the **Apply-to-docs Must
  Pause** requirement). Here the change has **already happened and is live** — we
  are not asking permission to change reality, we are recording reality that
  changed. There is no proposal to gate. So this skill has **no pause gate**, and
  resulting docs are born **`status: living`** (not `target`, not a proposal
  awaiting confirmation). The blast-radius survey still runs — but to inform the
  synthesis, not to ask "should we proceed?".

- **Source is our own decisions/episode, not external material (vs.
  ingest-reference).** ingest-reference brings in *outside* knowledge (meeting
  notes, RFCs, articles) that arrives through the inbox pipeline and becomes
  `reference`/`target` material. Here the source is the **working session we just
  finished** — our own decisions and rationale. It MAY still be persisted as a
  raw clipping for provenance (Step 1), but the extracted docs are first-class
  `living` truth claims about the system, not frozen external references.

- **Priority is the abstract, non-recoverable knowledge.** Implementation-level
  facts (what a function now does, which field was added) can be re-derived later
  from the code and existing docs. The conceptual *why* cannot: the principle
  that motivated the change, the goal it serves, the use-case it unblocks, the
  constraint it respects, and above all the **rationale behind each decision**.
  Bias every phase toward capturing these. A doc that merely restates what the
  code now does is low-value; a doc that captures *why we chose it* is the prize.

---

## This skill OWNS the episode (recursion / duplicate-review discipline)

Exactly like the other orchestrators' "orchestrator owns the episode" contract:

- reconcile-changes captures the single `START` timestamp (Step 0) and emits the
  **one** review summary for the whole episode (Step 8).
- Every sub-skill it invokes — `identify-key-concepts`, `map-concepts-to-docs`,
  `assess-blast-radius`, `synthesize-doc-changes`, and `cascade-check` — is a
  **nested invocation**: tell each one so. Nested sub-skills must NOT capture
  their own `START`, must NOT run `ldoc review new`, and must NOT re-invoke this
  orchestrator.

---

## Step 0 — Capture the episode start time

```bash
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

This timestamp generates the single review summary at the end of the episode.

---

## Step 1 — (optional) Anchor provenance with a session digest

The decisions being reconciled came from a working session. Anchoring a digest
of that session as a raw clipping gives every new doc an immutable provenance
target — the same discipline ingest-reference and apply-to-docs use, applied to
*our own* episode rather than external material.

Write a concise digest of the session: what was decided, what was built, and
**why** (the rationale is the most important part to preserve). Then persist it
to the raw tier:

```bash
python3 scripts/ldoc.py ingest-raw \
  --body "<session digest text>"   # or --body - to read from stdin
  --source "working-session <date/description>" \
  --title "Clipping: <short description of the session>"
```

Note the returned id: call it **DIGEST_ID**. It lives in `kb/01-raw/` — outside
the graph — and is the provenance anchor handed to `synthesize-doc-changes` in
Step 5. (Equivalently you may capture via `ldoc inbox add` then `ldoc promote`;
the digest is our own material, so going straight to `ingest-raw` is fine.)

This step is **optional but recommended**. If skipped, new docs are anchored by
their `requires`/`belongs_to` edges to existing docs instead; do not leave a
floating doc with no provenance and no graph edge.

---

## Step 2 — Extract concepts (invoke `identify-key-concepts`)

Invoke the **`identify-key-concepts`** skill on the session digest (or, if Step 1
was skipped, on the description of what changed), as a **nested invocation**.
Pass reconcile-changes's knobs:

> Extract concepts with **no upper limit** — a working session usually decided
> several things at once. Label each `Concept`. **Bias strongly toward the
> abstract, non-recoverable knowledge**: `principle`, `goal`, `use-case`,
> `constraint`, and the **rationale/why** behind each `decision`. Do NOT stop at
> `component`-type concepts that merely mirror what the code now does — those are
> re-derivable; the *why* is not. For every change made, ask "what principle,
> goal, or constraint motivated this, and what was the rationale?" and extract
> that as its own concept. Apply the splitting test: "This doc changes when ___"
> — if the blank covers more than one concern, split.

It returns a typed concept list (`Concept / Type / Asserts`) in context. Keep it
for Step 3.

---

## Step 3 — Map concepts to existing docs (invoke `map-concepts-to-docs`)

Invoke the **`map-concepts-to-docs`** skill with the concept list from Step 2, as
a **nested invocation**. Emphasis: **heavy dedup**. Because we are reconciling a
gap rather than introducing wholly new knowledge, **many concepts will already
have a doc** that is now stale or partially superseded. For each concept decide
update-vs-create: prefer revising or strengthening an existing doc over creating
a near-duplicate. It returns a relationship verdict map (`compatible` /
`partial-supersession` / `full-supersession` / `conflict-unresolved`) with a
planned action per concept. (Read-only — safe to run via `context: fork` if the
store is large.)

**Correcting stale existing docs is the highest-value output** — they have
dependents that cascade-check will propagate to; freshly created docs have none.

---

## Step 4 — Assess the blast radius (invoke `assess-blast-radius`)

Invoke the **`assess-blast-radius`** skill from every non-`compatible` match in
the Step 3 map, as a **nested invocation**, passing the session digest as the
change description. It walks the graph and returns the **complete impact set**
with verdicts and the frozen-doc rule applied. (Read-only — safe to run via
`context: fork` if the graph is large.)

**No pause gate.** Unlike apply-to-docs, reconcile-changes does NOT halt on a
large blast radius — the change is already real, so there is nothing to ask
permission for. The impact set exists to *inform the synthesis* (so it writes a
coherent batch) and to surface `conflict-unresolved` docs. If any
`conflict-unresolved` docs appear — meaning reality as we just lived it
contradicts a frozen/deprecated doc or a doc the synthesis cannot mechanically
reconcile — surface those specific conflicts to the user for judgment before
writing them, but do not gate the rest of the batch on a size threshold.

---

## Step 5 — Batch-synthesize all changes (invoke `synthesize-doc-changes`)

Invoke the **`synthesize-doc-changes`** skill, as a **nested invocation**,
handing it:

- the complete impact set from Step 4 (each affected doc with its verdict),
- the concept list from Step 2 (for new-doc creation),
- the provenance anchor **DIGEST_ID** from Step 1 (every new doc gets
  `--provenance <DIGEST_ID>`; duplicated/strengthened concepts link DIGEST_ID
  into an existing doc's `provenance` instead of creating a new doc),
- the **born-`living` knob**: new docs describe reality that already exists, so
  they are created with **`--status living`**, never `target` and never a
  proposal. (A concept describing something decided-but-explicitly-not-yet-built
  is the only exception and takes `target`; the default here is `living`.)

It writes deprecations → revisions → new docs in one coherent batch, upstream →
downstream, and returns the list of writes performed in context for the report.
(This phase runs inline — it needs the whole impact set in view.)

---

## Step 6 — Cascade from corrected docs (invoke `cascade-check`, nested)

After Step 5 corrects or deprecates existing docs, invoke the **`cascade-check`**
skill from **those corrected/deprecated docs** (not from freshly created docs —
new docs have no dependents and surface nothing when cascaded from). Tell
cascade-check this is a **nested invocation** so it does not emit its own review
summary.

---

## Step 7 — Validate the store

After all writes and cascades, confirm structural soundness:

```bash
python3 scripts/ldoc.py validate
```

Address any ERRORs before finishing. Surface WARNINGs to the user for review. Do
NOT reindex here — leave that to the maintenance cadence / a later explicit pass.

---

## Step 8 — Report and review summary (FINAL step)

Print a concise summary:

```
reconcile-changes — complete
Session: "<one-line description of what was decided/built>"
DIGEST_ID: <id>   kb/01-raw/<id>.md   — session digest (provenance anchor; not in graph)
                  (or "skipped — no digest clipping")

Concepts identified: N   (abstract/why-priority)
  "<concept>"  type: <type>  →  <action taken>

Docs changed:
  <id>  "<title>"  created     — born living; new doc for concept "<concept>"
  <id>  "<title>"  revised     — <one-line: what changed>
  <id>  "<title>"  deprecated  — superseded by <REPLACEMENT_ID>

Unchanged docs (compatible / inconsequential):
  <id>  "<title>"

Cascade summary: <N neighbors evaluated — list each id: verdict>
Validation: <N docs scanned — clean | N errors, N warnings>
```

Then emit the single review summary for the whole episode. reconcile-changes owns
it (the nested sub-skills never emit one):

```bash
python3 scripts/ldoc.py review new --since "$START"
```

Report the returned review id:

```
Review summary created: <id>   (kb/reviews/<id>.md)
```

Review is **post-hoc and non-gating**: it records the reconcile episode for later
signoff and never blocks the change.

---

## Body-content rule (store-wide convention)

Doc bodies describe the decision or mental model — what is true and **why**. They
do NOT narrate implementation state, absence, or history. Because reconcile-changes
records reality that already exists, born-`living` is the norm and the body
simply states the current truth and its rationale; it does not say "this was just
built" or narrate the session. If a concept is decided-but-explicitly-unbuilt,
express that gap with `status: target` — the body need not say so.

---

## Checklist before finishing

- [ ] Concept extraction biased toward principle/goal/use-case/constraint and the rationale/why — not just components mirroring code.
- [ ] map-concepts-to-docs ran with heavy dedup; existing docs revised in preference to near-duplicate new docs.
- [ ] No pause gate was applied (this skill records reality, not a proposal).
- [ ] New docs born `status: living` (only decided-but-unbuilt concepts take `target`).
- [ ] Every new doc has provenance (DIGEST_ID) or a genuine `requires`/`belongs_to` edge — no floating docs.
- [ ] cascade-check ran from corrected/deprecated existing docs (not from fresh docs).
- [ ] Validate is 0 errors. No reindex (left to maintenance cadence).
- [ ] Exactly one review summary emitted, owned by this orchestrator.
