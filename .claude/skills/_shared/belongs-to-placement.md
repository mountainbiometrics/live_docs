# What makes a good `belongs_to` placement

Single source of truth for every actor that places or re-places a doc in the
hierarchy — the ingest/apply writer at doc birth and the gardening refiner with
full-store context. Read and apply this policy; do not paraphrase from memory.

## What the hierarchy means

`belongs_to` is the **system's mental model**, not a mirror of the file tree. It
should **generally match the code structure** — so a scoped decision lands where
the code that honors it lives — but it is a **hybrid with the mental model of the
system**: code isn't always organized well, and the docs exist to explain the
*system*, not merely the codebase. Where the two diverge, **follow the mental
model** and let the tree teach a reader how the system actually hangs together.

Placement also carries **scope**: a decision binds at the level it is placed.
Put "use Redis for caching" under the project that made that call and it binds
that project, not its siblings; leave a doc with no `belongs_to` and it is
**global** — which is right for genuinely cross-cutting architectural decisions
and wrong for one that should bind only a single subtree. (See the doc-types
shared definition; effective scope is the union along the `belongs_to` ancestry.)

## Right-sizing the tree (shape)

The hierarchy should be a **roughly balanced tree** — dense enough that groupings
are meaningful, not so flat that a reader must scan a long sibling list to find
anything. The governing principle is **width proportional to depth**: a shallower
tree tolerates fewer children per node; a deeper tree can support more. There is
no fixed target — the goal is **search balance**: the trade between how much you
take in at a glance and how far you must dig to reach specifics.

The common failure in practice is the **overly wide branch** — a signpost with
many direct children that could cluster into a few sub-themes. This collapses
depth to save navigation steps but shifts the cost onto the reader, who must scan
every sibling at once. The fix is structural: introduce intermediate signposts
where children cluster into sub-themes, and re-home them one level down (the
branch-level analogue of decompose).

The rarer failure is the opposite: a chain of single-child signposts that forces
many hops to reach anything. If a path narrows to one or two children per level
for several levels, consider collapsing it.

This is the operative form of rule 4 below.

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
`--belongs-to <parent-id>` on `ldoc new` (alongside the required `--label`).
Gardening refines later; you **originate** placement, not defer entirely to
gardening.

## At gardening (full-store refiner)

You have the whole store. Second-guess birth placements, home orphans, split
overgrown branches, and move miscategorized members — always applying the same
five rules above.
