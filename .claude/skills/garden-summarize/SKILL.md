---
name: garden-summarize
user-invocable: false
description: >
  Gardening phase: given a descendant-bearing doc, write its body as an
  orientation guide and set a tight frontmatter summary. Synthesize, do not
  concatenate. Invoked by garden-hierarchy, cascade-check, and the garden
  dispatcher — never an episode owner when nested.
---

# garden-summarize — Write a signpost's orientation guide

**Contract:** nested phase only unless the user explicitly invoked the
`summarize-descendants` alias as a standalone episode (rare). When nested: capture
no START, run no `cascade-check`, emit no review — report changed ids only.

Applies to **any descendant-bearing doc** (target of `belongs_to` edges), any
`type`. Two outputs:

1. **Body** — synthesized orientation guide (no length limit). Synthesize, do not
   concatenate. **No `## Map` or member enumeration** — membership lives in edges.
2. **Frontmatter `summary`** — tight 1–3 sentences (≤ ~50 words), signpost only.

---

## Procedure

1. Load parent and members:
   ```bash
   ldoc show <parent-id>
   ldoc neighbors <parent-id> --kind dependents --json
   ```
2. Read each live member (`ldoc show <member-id>`); skip `deprecated` from the
   live guide.
3. Write body prose only (orientation, contributions, tensions, where to start).
   Reference members via `[[<member-id>]]` wiki-links.
4. Apply:
   ```bash
   ldoc set <parent-id> --body -
   ldoc set <parent-id> --summary "<tight signpost>"
   ldoc history <parent-id> --add "garden-summarize: synthesized overview over <N> members"
   ```

Cascade-sensitive: re-run whenever a member changes substantively (see
`cascade-check` descendant-summary rule).

---

## Output

```
garden — phase: summarize
Scanned: 1 signpost (<parent-id>), N members
Findings:
  …
Applied: synthesized <parent-id>
Changed-ids: [<parent-id>]
```
