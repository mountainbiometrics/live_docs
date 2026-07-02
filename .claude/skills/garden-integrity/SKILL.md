---
name: garden-integrity
user-invocable: false
description: >
  Gardening phase: mechanical structural repair — broken requires/belongs_to
  refs, missing required fields, id != filename, deprecated without
  superseded_by. Wraps ldoc validate and applies fixes (vs validate which only
  reports). Nested phase; garden dispatcher owns the episode.
---

# garden-integrity — Structural repair (form phase)

**Contract:** nested phase only. Capture no START, run no `cascade-check`, emit
no review. Apply mechanical fixes; report changed ids.

Objective/mechanical — distinct from `garden-refine` (editorial surface quality).

---

## Procedure

Start with:
```bash
ldoc validate
```

Then complement with graph checks:

1. **Broken hard-edge references** — for each broken `requires` or `belongs_to`,
   remove or correct via `ldoc unlink` / `ldoc link`.
2. **Orphans** — query fresh:
   ```bash
   ldoc orphans
   ```
   Skip frozen/`reference` docs and `type: type` schema docs. **Report** genuine
   orphans as a structural observation in the output — do NOT home them here.
   Homing requires full-store editorial judgment; that is `garden-hierarchy`'s
   job (a claim should have exactly one responsible doc; two owners = no owner). Forcing a `belongs_to` to close
   a defect is exactly the bad placement rule 5 forbids. Exception: a genuinely
   dangling orphan that has no plausible home and no dependents may be deprecated
   with `## Correction` + `--superseded-by`.
3. **Missing required fields** — apply via `ldoc set`.
4. **id != filename** — fix frontmatter id to match filename stem; do NOT rename
   files.
5. **Deprecated without superseded_by** — add `--superseded-by` or revert status.

Pass `--note "garden-integrity: …"` on each mutating command so the note is atomic
with the fix.

---

## Output

```
garden — phase: integrity
Scanned: N docs (validate + orphans)
Findings:
  <id>  — <issue>
Actions:
  [1] …
Applied: [list]
Changed-ids: [id, …]
```
