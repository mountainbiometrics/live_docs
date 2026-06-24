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

Singular ownership (see `20260624172648`): a claim with three partial owners has
no real owner.

---

## Signals

1. **Near-duplicates** — same claim in ≥2 docs (dedup notion from
   `map-concepts-to-docs`).
2. **Shared-ownership smell** — one responsibility spread thin; none fully owns it.
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
