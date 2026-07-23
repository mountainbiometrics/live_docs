# Regression notes — reconcile-changes

Anchors for refinement. Reconstructed 2026-07-23; replace with cited happy-path
outputs when available.

## Known-good properties (must keep permitting)

1. **Born-living, no pause gate.** Already-real changes are recorded, not
   proposed; blast-radius informs synthesis, does not ask permission.
2. **Abstract/why priority over code-mirroring components.** Implementation facts
   the code can re-derive are low-value; principles, goals, use-cases,
   constraints, and decision rationale are the prize.
3. **Heavy dedup.** Prefer revising existing docs over near-duplicate creates.
4. **Optional session digest as provenance anchor.** New docs wire
   `--provenance DIGEST_ID` (or genuine requires/belongs_to) — no floaters.
5. **One episode review**, owned by this orchestrator; nested phases emit none.
6. **Validate after writes**; no reindex in-episode.

## Known failure (2026-07-23 panelists)

Despite the why-priority knob, a large reconcile still produced a
decision-inventory first pass; user correction was required to elevate root
principles/constraints. Review close did not surface the type-mix / naming /
level smells.

## Newly discovered good-output property (2026-07-23)

7. **Root-over-decision shape.** A successful reconcile concept list / write set
   is dominated by principles/constraints/requirements/goals; decisions exist as
   thin `requires`-linked nodes, not as the primary inventory.
