# Regression notes — identify-key-concepts

Anchors for refinement. Reconstructed 2026-07-23 from skill intent + store
principles; replace with cited happy-path outputs when available.

## Known-good properties (must keep permitting)

1. **Typed durable claims, not implementation steps.** "Add a schema field" is
   not a concept; "edge metadata must include weight" is.
2. **Presupposed roots are fair game.** Goals/principles/requirements implied by
   the text may be extracted even when not stated as headings — but only when
   the input actually depends on them (not a free-floating invented why-chain).
3. **Doc-types ladder still applies.** Existential "a thing exists" → component;
   how-to → guide; external force → constraint; must-hold property → requirement;
   bedrock value → principle; only then a scoped choice-among-alternatives →
   decision.
4. **No KB queries, no writes.** Emit `Concept / Type / Asserts` only; the caller
   owns mapping and synthesis.
5. **Splitting test is opt-in.** Only when the calling flow asks for it.

## Known failure (2026-07-23 panelists reconcile / apply)

Given a working-session full of built decisions, extraction inventoried
*decisions* as first-class concepts and left the motivating principles /
constraints / requirements as rationale prose inside those decisions. User had
to mid-flight correct toward root principles/constraints/goals as first-class,
with decisions as thin dependents. (Method note: "5-whys" was illustrative of
seeking roots — not a mandated procedure.)

## Newly discovered good-output property (2026-07-23)

6. **Root-over-decision.** When both a why-root and a concrete choice are in the
   input, the concept list carries both as separate typed concepts — not one
   decision whose Asserts embeds the root. Decisions remain extractable (they
   model relations); they are not the inventory unit.
