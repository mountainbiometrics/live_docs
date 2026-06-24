---
name: garden-refine
user-invocable: false
description: >
  Gardening phase: sampling-based surface-quality pass — truncated titles/labels,
  summary quality, body-shape consistency, schema normalization (no alias JSON),
  and keywords curation. Catches sporadic agentic formatting drift. Nested phase;
  garden dispatcher owns the episode.
---

# garden-refine — Surface quality and findability (form phase)

**Contract:** nested phase only. Capture no START, run no `cascade-check`, emit
no review. All writes non-destructive to meaning; history entry on each touch.

Agentic pipelines produce intermittent inconsistency (see `20260624172719`) —
**sample**, don't full-scan every doc unless triage flags many issues.

Default sample size: **10–20 random living docs**, plus any docs flagged by
dispatcher triage (e.g. near-duplicate titles from a cheap `ldoc ls` skim).

---

## Checks

1. **Truncated / lazy labels & titles** — semantic truncations `validate` cannot
   catch ("ddl entities are", "State Policy is"). Rewrite via
   `ldoc set --title/--label` when not a complete noun phrase.
2. **Summary presence & quality** — real 1–3 sentence signpost, not a fragment or
   body first-line copy. `ldoc set --summary`.
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
5. **Keywords curation** — populate/curate `keywords` (findability synonyms,
   distinct from `domain`):
   ```bash
   ldoc set <id> --keywords "synonym1,synonym2,alias"
   ```
   Terms a searcher might type; no governance bar.

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
