---
name: garden-domains
user-invocable: false
description: >
  Gardening phase: cross-cutting domain tag curation — the ≥2-scopes test, align
  untagged docs, retire/split stale or over-broad domains. Orthogonal to tree
  topology; kept separate from garden-hierarchy. Nested phase; garden dispatcher
  owns the episode.
---

# garden-domains — Domain tag curation (structure phase)

**Contract:** nested phase only. Capture no START, run no `cascade-check`, emit
no review.

Read governing docs once — do not re-derive the model:
- `scope` (topological): `ldoc show 20260619235018`
- `domain` (cross-cutting tag): `ldoc show 20260615203839`
- `domain` vs `keywords`: `ldoc show 20260623233935`

`domain` is **not** `keywords`. Domain carries a governance bar; keywords do not.

---

## Procedure

1. Survey recurring cross-cutting concerns: `relates`/`requires` neighborhoods
   that **cross subsystem boundaries**, repeated vocabulary in titles/summaries,
   co-edited clusters. Ignore universal `requires → Foundational Principles` edges.
2. For each candidate cluster, compute each member's **effective scope** and apply
   the **≥2-scopes test**. Keep only clusters spanning two or more distinct scopes.
3. For each surviving domain, propose name (reuse existing strings; watch synonym
   drift), doc set, and one-line justification naming which scopes it cross-cuts.
4. **Align untagged docs** — `ldoc set <id> --domain <name>` where clearly belongs.
5. **Retire / split stale domains** — collapsed to one scope, or absorbed two
   unrelated concerns. Under-proposing is correct.

Record history on each touched doc. Do not invent domains to fill a slot.

---

## Output

```
garden — phase: domains
Scanned: N docs
Findings:
  …
Actions:
  …
Applied: [list]
Changed-ids: [id, …]
```
