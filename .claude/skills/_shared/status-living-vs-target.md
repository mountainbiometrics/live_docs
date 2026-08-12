# Status: living vs target — the shared definition

Single source of truth for assigning `status: living` vs `status: target` when
creating or revising truth-claim docs. Read and apply this; do not paraphrase
from memory. (`status: deprecated` / `status: reference` are separate lifecycle
values — this file does not govern them.) This file governs `status` alone —
settledness. It says nothing about `level` — claim authority, who decided this
and how deliberately — which is a separate axis and does not follow from
anything here.

## The most common failure mode this prevents

**Treating "not implemented yet" as `target`.** apply-to-docs runs minutes
before implementation; ingest often reads design prose that precedes code. If
"implementation lags the model" were enough to choose `target`, nearly every
new doc would be born `target`. That collapses the enum: `target` stops meaning
"deferred / not yet the paradigm," and starts meaning "we haven't typed the
code."

## Default

**Introduced concepts are `status: living` unless a narrow `target` test
passes.** Ambiguity → `living`, and surface the doc for human confirmation when
the deferral horizon is genuinely unclear. Do **not** prefer `target` on
ambiguity.

Do **not** inherit status from celebratory source language ("done," "shipped,"
"all todos complete"). That prose records intent at authoring time, not whether
the claim is the system's current paradigm.

## When `target` is correct

`status: target` means: this claim is the direction we are going, and it is
**explicitly not** the current paradigm yet — realization is deferred to future
notice (weeks/months or further), or will not be fully actualized on that
horizon (multi-piece migration, external dependencies, long cutover).

Concrete signals (any one can suffice when clear in the source):

- Explicit deferral: "next quarter," "after the migration," "not until…,"
  "future work," "we're not doing this yet."
- Mid-migration / partial cutover that will stay incomplete for weeks+.
- A component that **does not exist** and is not about to be built as current
  work; or a decision that commits to a shape we are deliberately not actualizing
  yet.

`target` is **not** correct merely because:

- apply-to-docs / revise is running just before current-work implementation, or
- code has not caught up to an in-force design the team is aligning to now, or
- the source is a plan/RFC that also contains in-force design (classify per
  concept, not per source document).

## Type fitness

| Type | `target`? |
|---|---|
| `decision`, `component` | Yes, when the deferral test above passes. |
| `principle`, `constraint`, `goal`, `requirement` | Almost never. Claiming them makes them **current** commitments. Lag is enforcement or achievement, not "we don't hold this yet." Prefer `living`. |
| `use-case`, `guide` | Judgment. A use-case for a product that does not exist yet may be `target`; a guide for how we work today is `living`. |
| `reference` | Use `status: reference` (frozen material), not this axis. |

## Body vs status

Doc bodies state the claim and why — positively, present-tense. They do **not**
narrate implementation state, absence, or history. When realization is deferred,
`status: target` carries that gap; the body need not say so. (See also
`doc-style.md` on deferral/plan language in prose.)

## Orchestrator knobs (do not contradict this file)

- **reconcile-changes** — born-`living` is the norm (reality already changed);
  the only exception is decided-but-explicitly-unbuilt under the test above.
- **ingest-reference** — classify each concept by the test above; do not stamp
  a whole plan `living` or `target` from document tone.
- **apply-to-docs** — current-work concepts land `living`; `target` only with
  explicit deferral in the request.
