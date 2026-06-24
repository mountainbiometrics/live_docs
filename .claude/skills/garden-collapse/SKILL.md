---
name: garden-collapse
user-invocable: false
description: >
  Gardening phase: enforce singular ownership — merge near-duplicate docs and
  fold thin cruft into parents. The inverse of garden-decompose. Nested phase;
  garden dispatcher owns the episode and runs decompose before collapse in full
  sweeps.
---

# garden-collapse — Merge duplicates and fold cruft (atomicity phase)

**Contract:** nested phase only. Capture no START, run no `cascade-check`, emit
no review.

**Guardrail:** collapse and decompose are antagonists. Never fold/merge anything
that would trip decompose's "two reasons to change" test. In a full sweep,
decompose runs *before* this phase.

Singular ownership — a claim should have exactly one responsible doc; a claim with three partial owners has no real owner.

---

## Signals

1. **Near-duplicates** — same claim in ≥2 docs (dedup notion from
   `map-concepts-to-docs`).
2. **Shared-ownership smell** — one claim spread thin across several docs, each
   partially owning it, none fully. Detection: several docs whose summaries each
   restate a *slice* of the same claim; a claim you cannot point a single owner
   at. This is the headline signal for diffuse ownership — the half of the work
   that gets skipped when an agent only deduplicates and de-crufts. Do not skip it.
3. **Cruft** — `level: incidental`, no dependents, thin body, not navigationally
   useful alone — candidate to **fold** into parent without overloading parent.

---

## Moves

### Merge (duplicates)

Pick survivor; port unique content; deprecate others:
```bash
ldoc set <survivor-id> --body -   # merged body
ldoc set <loser-id> --status deprecated
ldoc link <loser-id> --superseded-by <survivor-id>
ldoc history <loser-id> --add "garden-collapse: merged into <survivor-id>"
```
Add `## Correction` on deprecated docs. Rewire inbound edges to survivor.

### Fold (cruft into parent)

Merge trivial child content into parent body; deprecate child; rewire edges.
**Only** when parent stays singular (would not become a decompose candidate).

Read and apply `.claude/skills/_shared/belongs-to-placement.md` when rewiring
the folded child's former member edges — you are re-placing docs; every actor
that does so reads the one policy.

### Consolidate (diffuse ownership)

When a claim is scattered across several docs each partially owning it and none
fully: designate ONE owner doc (an existing or newly created doc), port the
scattered fragments into it, then thin the others to `relates` pointers or
deprecate redundant ones. Distinct from Merge (which assumes near-duplicates of
the whole claim) and Fold (which assumes one trivially thin child). Signal: you
cannot point to a single owner without also pointing at its siblings.

```bash
ldoc set <owner-id> --body -          # consolidated body
ldoc link <partial-id> --relates <owner-id>
ldoc set <redundant-id> --status deprecated
ldoc link <redundant-id> --superseded-by <owner-id>
ldoc history <owner-id> --add "garden-collapse: consolidated ownership from <partial-ids>"
```

---

## Guard against episode oscillation

Do **not** merge or fold docs that were created by a `garden-decompose` split
earlier in this same episode. Recognizable by: two docs sharing a `superseded_by`
pointer to the same deprecated parent, or sibling docs whose ids were reported in
`garden-decompose`'s `Changed-ids` this episode. Collapsing them would undo the
split and produce an infinite decompose→collapse loop.

---

## Output

```
garden — phase: collapse
Scanned: N docs
Findings:
  …
Actions:
  …
Applied: [list]
Changed-ids: [id, …]
```
