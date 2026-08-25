---
name: garden-refine
user-invocable: false
description: >
  Gardening phase: sampling-based surface-quality pass — truncated titles/labels,
  summary quality, body-shape consistency, and schema normalization (no alias JSON).
  Catches sporadic agentic formatting drift. Nested phase; garden dispatcher owns
  the episode.
---

# garden-refine — Surface quality (form phase)

**Contract:** nested phase only. Capture no START, run no `cascade-check`, emit
no review. All writes non-destructive to meaning; pass `--note "garden-refine: …"`
on each mutating command so the provenance note is atomic with the edit.

Agentic pipelines produce intermittent, non-deterministic inconsistency — a structural property of multi-agent doc pipelines, not an occasional bug —
**sample**, don't full-scan every doc unless triage flags many issues.
Inconsistency is sporadic and unpredictably located; the intent is **progressive,
rotating coverage across runs**, not a one-shot random dip that keeps
re-inspecting the easy middle.

Default sample size: **10–20 living docs**, plus any docs flagged by dispatcher
triage (e.g. near-duplicate titles from a cheap `ldoc ls` skim). Bias the
sample toward:
- **Recently created docs** (high agentic-inconsistency risk; likely never
  refined): sort `ldoc ls --json` by `created` descending, sample from the top.
- **Docs with no prior `garden-refine:` history entry**: check `ldoc history
  <id>` on candidates — prefer docs whose history shows no previous refine pass.

This bias rotates coverage across runs without cross-run state. Do not
concentrate every pass on the same well-worn center of the store.

---

## Checks

1. **Truncated / lazy labels & titles** — semantic truncations `validate` cannot
   catch ("ddl entities are", "State Policy is"). Rewrite via
   `ldoc set --title/--label` when not a complete noun phrase.
2. **Summary presence & quality** — real 1–3 sentence signpost, not a fragment or
   body first-line copy, and in the plain register per
   `.claude/skills/_shared/doc-style.md` (no metaphor, no synonym rotation for
   established terms; the same check applies to sampled body prose).
   `ldoc set --summary`.
3. **Body-shape consistency** — lightly normalize clearly lazy shapes (e.g.
   `decision` with no context/decision structure). Don't impose rigid templates.
4. **Schema normalization** — fold legacy fields/enums to canonical per schema +
   `ldoc validate` output. No checked-in alias JSON. Common moves:
   - **Legacy key rename** (`depends`/`depend_on` → `requires`, `references` →
     `provenance`, `created_at` → `created`): `ldoc set` cannot rename unknown
     keys — edit the doc file directly (preserve canonical field order per
     `ldoc show` / schema), then run `ldoc validate`. Skip if no legacy keys
     appear in the sample.
   - `state: target` → `status: target`; drop `state` (via `ldoc set` + direct
     edit to remove the `state:` line).
   - `state: actual` → leave/set `status: living`; drop `state`.
   - Enum fixes via `ldoc set --status` / `--level`.
   - Legacy `keywords:` frontmatter key (retired field): drop the key if still
     present on a sampled doc.

---

## Output

```
garden — phase: refine
Scanned: N docs (sample)
Findings:
  …
Actions:
  …
Applied: [list]
Changed-ids: [id, …]
```
