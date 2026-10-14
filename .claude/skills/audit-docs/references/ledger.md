# Ledger — audit-docs

Edit history for skill refinements. Newest first.

## 2026-10-14 — Mechanism disagreement reported as a contradiction (Class A)

**Failure:** First run. The auditor correctly observed three docs narrating
token issuance differently, reported it as a plain-register contradiction,
and proposed a passing version that chose a mechanism; it also routed a
second unowned mechanism question (which credential kinds MCP writes accept)
to Considerations as a design question. The orchestrator forwarded it to the
owner. Owner: the audit is of the writing, not of the design; the writing
failure is mechanism stated as doctrine in three claims none of which owns
it.

**Class:** A. The skill's "Classify; do not ask" covered wording questions;
nothing said an inter-doc mechanism disagreement is over-specification, that
the passing version is removal, or that it never reaches Considerations.

**Diff:** SKILL.md "Classify; do not ask" gains the unowned-mechanism rule;
"Where a mechanism belongs" first asks whether any doc should hold the
mechanism. checks.md D gains "Mechanism narrated as doctrine", "Unowned
mechanism disagreement", and "Commanding prose", all pointing at the new
doc-style section.

**Amended same day (owner-flagged under-correction):** the first edit
kept the survival test as the judgment. Owner: a mechanism is never stated
unless the doc is the decision for it, and no fact outside the doc's own
claim is stated at all. The judgment zone now asks one question (is this doc
the decision for the mechanism it names?); checks.md D is `violates` with no
survival test, gains "Fact outside the claim", and the coupled-mechanism
check moves from `reads-as` to `violates`.

**Regression answers:** 1–4, 6 unchanged. 5 subject detail survives —
narrowed on purpose: only a decision's own chosen names survive. 7 no
wording question to the owner — widened: no mechanism question either.


## 2026-10-14 — v1 authored

**Occasion:** after an apply-to-docs episode landed 32 new docs and 5
revisions in one consumer store, the owner wanted an independent content
check against the writing standards, separate from garden (which writes and
samples) and from the write path (which carries the request's context). No
skill covered it.

**Sources:** the shared standards (`_shared/doc-style.md`,
`label-title-summary.md`, `doc-types.md`, `cruft-verdicts.md`, `facets.md`,
`domain-tagging.md`, `belongs-to-placement.md`) and the refinement ledgers of
synthesize-doc-changes, apply-to-docs, reconcile-changes, revise-doc,
identify-key-concepts, cascade-check, and ingest-reference, read for the
failures the owner has corrected repeatedly. `references/checks.md` is the
index from those failures to the governing sections.

**Requirement bins:**

- *Invariants:* read-only; standards read in full and cited; blind pass
  before sourced pass; the five-part finding shape; a verdict line per doc;
  `ldoc validate` run once rather than re-derived; no wording questions to
  the owner.
- *Judgment:* what each doc is for, read from its descriptors; where a
  mechanism belongs across the set (coupling); duplicated rules and their
  owner; severity order and reading depth; `reads-as` versus `violates` on
  borderline passages; pass-2 scope.
- *Scripts:* none. `ldoc validate` already owns the deterministic checks
  (ceilings, required fields, dangling refs). A detector for zero-edge
  principles or same-domain batches would be heuristic and is left to
  judgment.
- *Out of scope:* fixing anything (route findings to revise-doc or garden);
  graph consistency (cascade-check); sampling-based maintenance over the
  whole store (garden-refine); the question of whether the request itself
  was recorded correctly (apply-to-docs' own review).

**Declined:** a severity enum beyond the two tags (owner asked for a
quality check, not a triage system); a per-check pass/fail matrix per doc
(the verdict line plus finding ids carries the same information without a
grid that invites ticking).
