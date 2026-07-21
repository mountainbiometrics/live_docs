# Cruft verdicts — the shared vocabulary

Single source of truth for every actor that judges whether a doc has decayed
into cruft and decides what to do about it — the `garden-cruft` phase that runs
the pass, and any skill (synthesize-doc-changes, revise-doc, apply-to-docs,
ingest-reference) that wants to apply the same vocabulary inline, proactively,
at write time rather than only at gardening time. Read and apply this; do not
paraphrase from memory.

The *why* behind this pass: docs capture the *why* (decisions, rationale,
constraints, use-cases), not the *what* the code already encodes — docs lead,
code aligns; design knowledge is atomic and precisely editable like
well-factored code, not a replace-the-whole-blob snapshot; every non-signpost
doc must carry its why, and a what stated with no why is repaired or removed
(signposts excepted); gardening's real value is evaluative — judging when
something is redundant, idiotic, or no longer earning its place; and deletion is
the default retirement path when a doc's content is fully captured elsewhere,
with deprecation reserved for overturned beliefs worth preserving. This file is
the operative *how*.

## The detection lens

A doc captures the **current intent** — the principle / decision / constraint /
requirement in force that any code change should align to — **not a snapshot of
what the code does now.** Cruft is the gap that opens when a doc drifts from
that. In a scan, the signals that surface it (each routes to a verdict below):

- **Dead implementation *what* over a live *why*** — a still-current decision
  buried under removed or renamed code, or a doc whose subject is named after a
  class / function / module that was renamed or never built. The most common
  shape.
- **Wrong type** — e.g. a "have a module that does X" doc typed as a `decision`.
- **A *what* with no *why*** on a non-signpost doc.
- **Refactor-task-as-doc** — a chore step ("reorganize the tests", "delete the
  old names", "create these module files"); see the pre-filter below.
- **Cross-cluster duplication** — the same durable decision recorded once per
  subsystem it touches.
- **Mis-clustered survivor** — belongs under a different parent than its current,
  cruft-driven cluster.

**Detail that is incidental vs. detail that is the subject.** Not all
implementation-shaped language is cruft. A doc drifts into implementation
detail when a concrete name or shape stands in for a concept it merely
illustrates — e.g., a doc about retry behavior in general shouldn't lean on
the literal name of one function's retry-count parameter to make its point.
But when a doc's entire subject IS a decision about a concrete interface —
what a public contract's fields are called, what an enum's values are, what a
wire format looks like — naming those specifics is the decision, not detail
leaking in. Test: strip the specific name and ask whether the doc's claim
still makes sense. If yes, the name was incidental — strip it (this is
EXCAVATE below). If no, the name is what's being decided — keep it.

Do **not** lead with "wrong status" — status is usually not the cruft signal
(see calibration below).

### Pre-filter: refactor-plan clusters

Refactor-plan-shaped clusters over-decompose into chore docs. Before judging
each doc, apply:

> **If a doc's body is a step in a *completed* refactor plan AND the durable why
> already lives in the plan's `reference` doc → default REMOVE.**

This one rule typically decides a large fraction of a refactor cluster. Confirm
the why is genuinely captured in the plan's reference doc before removing; if the
step carries a durable decision the plan doc lacks, EXCAVATE it instead.

## The verdicts

Assign each doc exactly one verdict (the compounds below are the only stacks).

| Verdict | Apply when | Action |
|---|---|---|
| **KEEP** | Current, well-typed, carries its why. | Nothing. |
| **EXCAVATE** | The architectural decision is **still current** but the doc is buried under removed/renamed implementation detail. | Strip the dead *what*; keep the *why*. **Status was never wrong** — do not deprecate. |
| **EXCAVATE(rename)** | Sub-case of EXCAVATE: the doc's subject is named after a class / function / module that was renamed or never built. | Strip the dead symbol noun-phrase; keep the decision. Status was never wrong. |
| **RECLASSIFY→type** | The doc is the wrong type (e.g. a "have a module that does X" decision is really a `component` named "module for X"). | Re-type per `_shared/doc-types.md` and its "is this really a decision?" ladder. |
| **ADD-WHY** | A **non-signpost** doc states a *what* with no *why*. | Add the why (may cite its provenance doc); every non-signpost doc must carry its why. Signposts are the allowed exception. |
| **REMOVE** | No durable content not already captured elsewhere. | `ldoc rm` — deletion is the default retirement path when content is fully captured elsewhere. **Especially:** a doc that is a step in a *completed* refactor plan whose durable why already lives in the plan's `reference` doc → default REMOVE. |
| **MERGE→id** | Folds wholly into a sibling/target. | Port unique content into the target, deprecate or `ldoc rm` the loser. |
| **EXCAVATE→MERGE→id** | A doc that is *both* an excavate target *and* redundant with a sibling. | Distill the durable clause first, **then** fold it into the target and delete. |
| **RE-PARENT→signpost** | The survivor belongs under a different parent than its current (cruft-driven) cluster. | Re-home per `_shared/belongs-to-placement.md`. |

**EXCAVATE is the single most common shape** — the durable why survives while
the implementation cruft is stripped. It operationalizes docs-lead-code-aligns:
the doc keeps the *why* the code must align to, never a snapshot of the *what*.

## Applying the verdicts (existing ldoc only)

No new CLI flags — every action uses `ldoc set` / `rm` / `link` / `unlink`:

- **EXCAVATE / EXCAVATE(rename) / ADD-WHY** — rewrite the body via
  `ldoc set <id> --body - --note "garden-cruft: excavated — stripped <dead what>, kept the why"`
  (and `--summary` to match).
- **RECLASSIFY** — `ldoc set <id> --type <type> --note "garden-cruft: reclassified type"`.
- **REMOVE** — `ldoc rm <id>`; rewire any inbound edges first.
- **MERGE→id / EXCAVATE→MERGE→id** — port into the target via
  `ldoc set <target> --body - --note "garden-cruft: merged in <loser-id>"`, then
  deprecate (Correction + `superseded_by`) or `ldoc rm` the loser; rewire inbound
  edges to the target.
- **RE-PARENT→signpost** — `ldoc unlink <id> --belongs-to <old>` then
  `ldoc link <id> --belongs-to <new>`.

## Calibration learnings (apply as guidance)

These three corrections keep the pass from mis-firing:

1. **Status is usually NOT the cruft signal.** Do not lead with "wrong status" —
   in practice nearly every doc is correctly `living`/`reference`. The real cruft
   is (a) implementation-symbol names and (b) granularity (refactor-task-as-doc).
   EXCAVATE keeps status; it is not a status fix.

2. **Cross-cluster dedup is essential.** The same durable decision is often
   recorded once per subsystem it touches — the same serialization-boundary
   decision restated in each module that serializes. Distill the decision
   **once** and dedup across clusters, rather than excavating each copy in
   isolation.

3. **Deprecate vs delete vs excavate — keep them distinct.** EXCAVATE (keep the
   why, fix the what) is **NOT** deprecation. Deprecate only when a doc recorded
   a belief worth preserving as **overturned history** (per the deprecation
   protocol: `## Correction` + `superseded_by`). When the doc is simply redundant,
   REMOVE. When the why is still true and only the what rotted, EXCAVATE.
