# What makes a good `belongs_to` placement

Single source of truth for every actor that places or re-places a doc in the
hierarchy — the ingest/apply writer at doc birth and the gardening refiner with
full-store context. Read and apply this policy; do not paraphrase from memory.

## Rules

1. **Prefer the nearest coherent signpost over the root.** Place the doc under
   the most specific grouping that genuinely contains it — not at the top because
   the top is always a safe parent.

2. **A placement is a navigational claim, not a tag.** `belongs_to` asserts
   "this doc is part of, and would be orphaned without, that grouping." It is
   the membership/hierarchy axis — distinct from `domain`/`keywords` tags and from
   the logical `requires` web.

3. **One primary parent.** A doc declares the single grouping that defines it,
   not a scattering of weak memberships.

4. **"In the tree somewhere" is necessary but not sufficient.** Being placed at
   all is not the bar; it must be the *right* branch and a *right-sized* one —
   a branch that is still navigable, not an overgrown catch-all.

5. **When no good parent is visible, defer rather than force one.** A bad
   placement is worse than a deferred one. Leave it for gardening with full-store
   context rather than wiring a misleading membership.

## Resolving the semi-adequate vs defer tension

Rule 5 says defer when no good parent is visible; `20260623233949` says ingest
should originate a *semi-adequate* parent. These collide at the margin. The
adjudicating test: **"Would this placement mislead a navigator?"**

- If no — originate it even if imperfect. A slightly-off-but-not-misleading home
  is better than leaving the doc homeless; gardening refines it later.
- If yes — defer (omit `--belongs-to`). A misleading membership is worse than a
  deferred one; do not force a home to avoid an orphan.

## At doc birth (ingest / apply writer)

You already hold the concepts and edges in hand. Pick the **best visible**
signpost from that local context — semi-adequate, not perfect. Wire
`--belongs-to <parent-id>` on `ldoc new`. Gardening refines later; you
**originate** placement, not defer entirely to gardening.

## At gardening (full-store refiner)

You have the whole store. Second-guess birth placements, home orphans, split
overgrown branches, and move miscategorized members — always applying the same
five rules above.
