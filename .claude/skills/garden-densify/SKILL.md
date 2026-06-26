---
name: garden-densify
user-invocable: false
description: >
  Gardening phase: build the missing/better edges so the graph becomes
  well-connected and cascade can self-heal — materialize prose wikilinks into
  real edges, and add genuine missing dependencies (favoring cascade-HARD
  `requires`). Nested phase; garden dispatcher owns the episode and runs densify
  after structure is settled, before form.
---

# garden-densify — Build missing edges (structure phase)

**Contract:** nested phase only. Capture no START, run no `cascade-check`, emit
no review. Apply the edge writes you judge correct; report changed ids (the docs
whose edge lists you touched) for the dispatcher to union, cascade, and review
once at episode close.

A doc graph only self-heals where edges exist. When a real relationship lives
only in prose — or is missing entirely — cascade cannot reach the doc that
should have been updated, and the store drifts silently. This phase closes that
gap: it makes the *edges* match the *relationships that are actually true*.

---

## The edge model you are wiring (respect it exactly)

There are five edge types; only two cascade.

| Edge | Meaning | Cascades? |
|------|---------|-----------|
| `belongs_to` | hierarchy / membership; an acyclic DAG | **HARD** |
| `requires` | existential dependency — the doc is meaningless or wrong without the target; may cycle | **HARD** |
| `relates` | soft see-also; no dependency claim | no |
| `provenance` | soft; where this was derived from | no |
| `superseded_by` | points a deprecated doc at its replacement | (deprecation) |

The cascade consequence is the whole point of this phase: **`relates` and
`provenance` do not propagate.** Building only soft edges connects the graph
*visually* but buys **nothing** for self-healing. When a relationship is a true
existential dependency, the edge that makes cascade reach the right doc is
`requires` (or `belongs_to` for membership) — pick that one, not a safe-looking
`relates`.

---

## What densify does

### 1. Materialize prose wikilinks into real edges (the deterministic win)

Signpost and orientation bodies narrate relationships as `[[id]]` wikilinks, but
nothing turns those mentions into edges. This is the highest-yield, lowest-risk
work in the phase: the relationship is already asserted in prose; you are only
making the graph agree with the doc.

For each doc in scope:

1. Scan the body for `[[id]]` references.
2. For each referenced id **not already present in that doc's edge lists**,
   choose the edge type **by judgment per link** from how the prose uses it:
   - the link names a parent / a member-of relationship → `belongs_to`
   - the doc is meaningless or wrong without the linked doc → `requires`
   - the prose merely points "see also" / "related" / "for context" → `relates`
3. Add that one edge.

Do **not** blindly assign a single type to every wikilink. The same body can
narrate a parent (membership), a hard dependency, and a see-also in three
adjacent sentences; read each one.

### 2. Find genuine missing dependencies and add them

Beyond what prose already names, look for real dependencies the doc never
encoded as any edge. Prioritize the cascade-HARD `requires`: a decision that
would be wrong if some upstream constraint changed, a component that cannot stand
without the principle it implements. Build the edge that makes a future change to
the target *reach* this doc through cascade.

Soft edges (`relates`, `provenance`) are fine to add where that is genuinely the
relationship — but adding them is not the goal. If you find yourself only ever
adding `relates`, you are not densifying for self-healing; re-ask whether the
relationship is actually existential.

---

## Scope and restraint

- Operate within **one cluster / `scope` at a time** — a connected
  neighborhood you can hold in mind — not the whole store at once. Coherence
  beats coverage.
- **Do not over-link.** An edge must mean exactly what its type says. Never
  manufacture a `requires` to "improve connectivity" — a false existential
  dependency makes cascade fire on docs that did not actually need updating,
  which is worse than a missing edge. When in doubt between `requires` and
  `relates`, ask: *if the target changed, would this doc be wrong?* Yes →
  `requires`; merely *interesting* → `relates`; neither → no edge.
- Respect `belongs_to` acyclicity — never add a membership edge that would
  create a cycle.
- When the edge you add is a `belongs_to` re-/placement, read and apply
  `.claude/skills/_shared/belongs-to-placement.md`.

---

## Procedure

1. Load the candidate cluster (a `scope`, a signpost's subtree, or a small set
   from `ldoc ls --json` + `ldoc show <id>`).
2. For each doc, scan the body for `[[id]]` wikilinks and diff against its
   existing edge lists.
3. Materialize each missing wikilink with the per-link type judgment above.
4. Scan for genuine missing dependencies not named in prose; add `requires`
   (preferred for existential deps) / `belongs_to` / `relates` as the
   relationship truly is.
5. Apply with `ldoc link` only — no invented flags. Append a `garden-densify:`
   history entry on each doc whose edges you changed.
6. Report changed ids. Do **not** cascade, summarize, or review.

---

## Output

```
garden — phase: densify
Scanned: N docs
Findings:
  <id>  "<title>"  — <n> prose wikilinks unmaterialized; <m> missing deps
Actions:
  [1] LINK <id> --requires <target> — existential dep; cascade now reaches it
  [2] LINK <id> --belongs-to <parent> — prose named the parent; materialized
  [3] LINK <id> --relates <target> — see-also from body
Applied: [list]
Changed-ids: [id, …]
```
