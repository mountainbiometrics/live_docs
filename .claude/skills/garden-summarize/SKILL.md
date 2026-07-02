---
name: garden-summarize
user-invocable: false
user-invocable: true
description: >
  Gardening phase: given a descendant-bearing doc, write its body as an
  orientation guide and set a tight frontmatter summary. Synthesize, do not
  concatenate. Invoked by garden-hierarchy, cascade-check, and the garden
  dispatcher — never an episode owner when nested. May also be invoked
  standalone to refresh a single signpost's overview (rare).
---

# garden-summarize — Write a signpost's orientation guide

**Contract:** a nested phase by default; can also be invoked standalone (rare).

- **Standalone** (user invoked `garden-summarize` directly): it owns the episode.
  Open a session (`ldoc session start`, exported), run the procedure, validate,
  then close it (`ldoc session close`) — closing mints the single review. Use the
  `garden-summarize:` note prefix.
- **Nested** (called from `garden`, `garden-hierarchy`, or `cascade-check`): it
  inherits the ambient session — no `session start`, no `session close`, run no
  `cascade-check`, emit no review. The caller owns the session; report changed ids
  only.

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
   ldoc set <parent-id> --body - --note "garden-summarize: synthesized overview over <N> members"
   ldoc set <parent-id> --summary "<tight signpost>"
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
