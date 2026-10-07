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
walks that gap closed — the resulting docs are born `status: living` with
`realization: realized` for what the session built, because they describe
reality as it now stands.

**"Already real" governs `realization` only — it has no bearing on `intent`.**
`realization` answers "does this exist in the implementation?"; `intent`
answers "what did the person do to make this claim exist?" That code got
built, tested, and committed is evidence for the former, never for the latter
— an implementer's own convenience choice is `incidental` no matter how solid
the code behind it is (`.claude/skills/_shared/facets.md`, the evidence rule).
This distinction matters because a claim recorded above its real intent does
not sit inert: later changes compare against it, and one carrying lower
intent is written beside it instead of updating it. The worst case is a
convenience nobody asked for, recorded as `chosen`, sitting in the way of a
direction the person has actually asked for.
Read every "already real" instinct in this file as scoped to `realization`;
carrying it into `intent` is this skill's most common failure.

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
  resulting docs are born **`status: living`** and, for what was built,
  **`realization: realized`** (not a proposal awaiting confirmation). The blast-radius survey still runs — but to inform the
  synthesis, not to ask "should we proceed?".

- **Source is our own decisions/episode, not external material (vs.
  ingest-reference).** ingest-reference brings in *outside* knowledge (meeting
  notes, RFCs, articles) that arrives through the inbox pipeline and becomes
  `reference` material plus claims of mostly `incidental` intent. Here the source is the **working session we just
  finished** — our own decisions and rationale. It MAY still be persisted as a
  raw clipping for provenance (Step 1), but the extracted docs are first-class
  `living` truth claims about the system, not frozen external references.

- **Priority is the abstract, non-recoverable knowledge.** Implementation-level
  facts (what a function now does, which field was added) can be re-derived later
  from the code and existing docs — and often so can the bare decision outcomes.
  The conceptual *why* cannot: the principles, constraints, requirements, and
  goals that motivated the change. Bias every phase toward capturing those roots
  as first-class docs; keep decisions thin so their relations can be modeled.
  A doc that merely restates what was chosen (or what the code now does) is
  low-value; the why-web against which a future challenge can be re-weighed is
  the prize.

---

## You are the orchestrator — run every step through to Step 8

You run this skill end to end. Each sub-skill it names (`identify-key-concepts`,
`map-concepts-to-docs`, …) runs **inline, in this same turn**, and its result
feeds the step after it — running a sub-skill is never where you stop.

- reconcile-changes owns the episode — it opens the session (Step 0) and closes
  it into the **one** review for the whole episode (Step 8).
- The sub-skills it runs do no episode bookkeeping of their own — none opens or
  closes a session (no `session start`/`session close`).

---

## Step 0 — Open the editing session

```bash
export LDOC_SESSION=$(ldoc session start)
```

Read and apply `.claude/skills/_shared/session-lifecycle.md`. Closing this session
at the end of the episode mints the single review summary.

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
ldoc ingest-raw \
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

Run — but do not stop after — **`/identify-key-concepts`** on the session digest
(or, if Step 1 was skipped, on the description of what changed), then carry its
concept list into Step 3. Pass reconcile-changes's knobs:

> Extract every distinct durable concept — a working session usually decided
> several things at once. Label each `Concept`. **Root-over-decision is
> mandatory here** (see identify-key-concepts): prefer first-class `principle` /
> `constraint` / `requirement` / `goal` / `use-case` concepts — the
> non-recoverable why-web — over a flat inventory of `decision`s. When a
> decision is worth recording, keep it thin: its Asserts names the choice; the
> motivating root is a **separate** concept it will later `require`. Do **not**
> treat "rationale behind the decision" as license to leave the root as
> decision-body prose. Do NOT extract a concept of **any** type that merely
> restates what the code now does — a `constraint` or `requirement` that
> paraphrases a module's own comments is exactly as re-derivable as a
> `component`, and carrying a why-shaped type does not make it a why. Ask of
> each: would this still be knowable if the implementation were rewritten?
> Apply the splitting test: "This doc changes when ___" — if the blank covers
> more than one concern, split.

It returns a typed concept list (`Concept / Type / Asserts`) in context. Keep it
for Step 3.

---

## Step 3 — Map concepts to existing docs (invoke `map-concepts-to-docs`)

Run — but do not stop after — **`/map-concepts-to-docs`** with the concept list
from Step 2, then carry its verdict map into Step 4. Emphasis: **heavy dedup**.
Because we are reconciling a gap rather than introducing wholly new knowledge,
**many concepts will already have a doc** that is now stale or partially
superseded. For each concept decide update-vs-create: prefer revising or
strengthening an existing doc over creating a near-duplicate. It returns a
relationship verdict map (`compatible` / `partial-supersession` /
`full-supersession` / `conflict-unresolved`) with a planned action per concept.
(Read-only.)

**Correcting stale existing docs is the highest-value output** — they have
dependents that cascade-check will propagate to; freshly created docs have none.

---

## Step 4 — Assess the blast radius (invoke `assess-blast-radius`)

Run — but do not stop after — **`/assess-blast-radius`** from every
non-`compatible` match in the Step 3 map, passing the session digest as the
change description, then continue to Step 5. It walks the graph and returns the
**complete impact set** with verdicts and the frozen-doc rule applied.
(Read-only.)

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

Run — but do not stop after — **`/synthesize-doc-changes`**, handing it:

- the complete impact set from Step 4 (each affected doc with its verdict),
- the concept list from Step 2 (for new-doc creation),
- the provenance anchor **DIGEST_ID** from Step 1 (every new doc gets
  `--provenance <DIGEST_ID>`; duplicated/strengthened concepts link DIGEST_ID
  into an existing doc's `provenance` instead of creating a new doc),
- the **born-`living` knob**: new docs describe reality that already exists, so
  they are created with **`--status living`** and, for what the session built,
  **`--realization realized`** (with `--realization-refs` where the anchors are
  known). A concept the session decided but explicitly left unbuilt is
  `planned`, or `deferred` if it was put off.
- the **intent test** (`facets.md`, the evidence rule), applied per claim, not
  per batch: ask *what the person did*. An implementer's own convenience choice
  — never raised, requested, or chosen by the person — is `incidental`, however
  well-tested; built-and-committed is not a basis. Something the person stated
  in their own words is `requested` with those words as `--intent-basis`, and
  stays `requested` even when the code for it doesn't exist yet — that gap
  belongs to `realization`, not `intent`. Watch for the inverse too: a
  person-stated claim landing `incidental` while the convenience built in its
  place lands `chosen` inverts the record, which this test exists to catch.

Each claim carries the intent Step 5 gave it, and `map-concepts-to-docs`
compares that against the existing docs: a freshly built convenience does
not overturn what the person asked for by being newer.

It writes deprecations → revisions → new docs in one coherent batch, upstream →
downstream, and returns the list of writes performed in context for the report.
It needs the whole impact set in view, which is why it comes after Step 4.

**Do not write with raw `ldoc new`/`set` in its place.** This phase is the only
place the store's write-time discipline is reachable: label shape
(`_shared/label-title-summary.md`), `domain` vs `scope`
(`_shared/domain-tagging.md`), body style and no-coupling
(`_shared/doc-style.md`), and placement (`_shared/belongs-to-placement.md`).
An agent that hands the batch to `ldoc` directly will produce docs that
validate cleanly and still break every one of those rules, because nothing
downstream checks them.

---

## Step 6 — Cascade from corrected docs (run `/cascade-check`)

After Step 5 corrects or deprecates existing docs, run **`/cascade-check`** from
**those corrected/deprecated docs** (not from freshly created docs — new docs
have no dependents and surface nothing when cascaded from), then continue to
Step 7. (reconcile-changes owns the single episode review summary — cascade-check
does not emit its own.)

---

## Step 7 — Validate the store

After all writes and cascades, confirm structural soundness:

```bash
ldoc validate
```

Address any ERRORs before finishing. Surface WARNINGs to the user for review. Do
NOT reindex here — leave that to the maintenance cadence / a later explicit pass.

---

## Step 8 — Report and review summary (FINAL step)

**Batch self-check (before close).** Spot-check the writes you just made against
the source digest — these are process smells, not a truth oracle:

- **Type mix:** if you claimed why-priority and nearly everything created is
  `decision`, revisit extraction/synthesis before closing.
- **Labels:** two separate tests, and passing one does not pass the other.
  *Vocabulary* — a label absent from the digest/session vocabulary → rename;
  prefer the user's words. *Shape* — read each label alone and ask what a
  reader would expect to learn by opening it. A label that already states the
  conclusion ("Presence Is The Ceiling", "Worth Is What Is Lost") answers
  instead of naming, and is wrong even when every word came from the session.
- **Domain vs scope:** if the batch shares one domain that names the subsystem
  the docs live in, that is a `scope` mis-tagged as a `domain` — put `scope` on
  the anchor and let the members inherit.
- **Intent:** a batch of new docs all `requested` or `chosen` with one shared
  basis is almost certainly wrong — unconfirmed articulations are
  `incidental`.
- **Intent vs. realization:** if intent tracks what got implemented more than
  what the person did — everything shipped `chosen`, everything unbuilt
  `incidental` — that correlation is itself the smell; re-run the intent test
  (Step 5) per claim, not per batch.
- **Intent comparison skipped:** a new claim was written over an existing
  doc without `map-concepts-to-docs` comparing their intents.
- **Source string:** if the digest was agent-authored, its `--source` must not
  claim `user-request`.

Print a concise summary:

```
reconcile-changes — complete
Session: "<one-line description of what was decided/built>"
DIGEST_ID: <id>   kb/01-raw/<id>.md   — session digest (provenance anchor; not in graph)
                  (or "skipped — no digest clipping")

Concepts identified: N   (abstract/why-priority)
  "<concept>"  type: <type>  →  <action taken>

Docs changed:
  <id>  "<title>"  created     — born living, <realization>; new doc for concept "<concept>"
  <id>  "<title>"  revised     — <one-line: what changed>
  <id>  "<title>"  deprecated  — superseded by <REPLACEMENT_ID>

Unchanged docs (compatible / inconsequential):
  <id>  "<title>"

Cascade summary: <N neighbors evaluated — list each id: verdict>
Validation: <N docs scanned — clean | N errors, N warnings>
Self-check: <type-mix / labels / intent / source — ok or what you fixed>
```

Then close the session, minting the single review for the whole episode.
reconcile-changes owns it (the nested sub-skills never open or close one):

```bash
ldoc session close --summary "<one-line agent recap of the episode>"
```

The review is built from the session's change log; confirm `touched` reflects the
episode's changes. Report the returned review id:

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
built" or narrate the session — that is `realization` (`facets.md`).

---

## Checklist before finishing

- [ ] Concept extraction used root-over-decision: principles/constraints/requirements/goals first-class; decisions thin — not just components mirroring code.
- [ ] map-concepts-to-docs ran with heavy dedup; existing docs revised in preference to near-duplicate new docs.
- [ ] No pause gate was applied (this skill records reality, not a proposal).
- [ ] New docs born `status: living`, with realization from the implementation (`realized` for what was built; `planned`/`deferred` only for decided-but-unbuilt).
- [ ] Intent follows the evidence rule (Step 5): what the person did, with a basis for every `requested`/`chosen` — not whether it's built or has a provenance edge.
- [ ] Every new doc has provenance (DIGEST_ID) or a genuine `requires`/`belongs_to` edge — no floating docs.
- [ ] cascade-check ran from corrected/deprecated existing docs (not from fresh docs).
- [ ] Batch self-check (type-mix / labels / intent / source) done.
- [ ] Validate is 0 errors. No reindex (left to maintenance cadence).
- [ ] Exactly one review summary emitted, owned by this orchestrator.
