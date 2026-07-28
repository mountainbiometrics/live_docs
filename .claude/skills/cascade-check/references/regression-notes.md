# Regression notes — cascade-check

Anchors for refinement. Created 2026-07-28 with the restated-ownership repair.

## Known-good properties (must keep permitting)

1. **Two passes, cleanly separated.** Pass 1 read-only verdicts; Pass 2 batch
   writes — never interleave.
2. **Bias to inconsequential** when the relationship is weak or tangential.
3. **Frozen docs are never rewritten** to track current state (incompatible at
   most).
4. **Descendant-summary rule** — substantive member changes cascade to parents
   via `garden-summarize`, not hand-patched member lists in the parent body.
5. **Restated-ownership repair.** If a neighbor is stale only because it
   restates an owned claim/enumeration, collapse to `[[owner]]` (+ edges) —
   do not synchronize the shadow list. (sinai soft-atomic cleanup 2026-07-28;
   failure mode was N-doc list-sync on catalog membership change.)

## Known failure (2026-07-28)

Worked example previously taught: neighbor enumerates cascade targets → rewrite
the list to include the new item. That produced insubstantial multi-doc prose
cascades whenever a catalog membership changed.
