---
name: garden-decompose
user-invocable: false
description: >
  Gardening phase: find docs carrying more than one responsibility and split
  them. Signals include multiple unrelated body sections, hot-file history,
  long requires lists, and compound titles. A nested phase sub-skill — never an
  episode owner; the garden dispatcher owns START, cascade, and review.
---

# garden-decompose — Split overloaded docs (atomicity phase)

**Contract:** nested phase only. Capture no START, run no `cascade-check`, emit
no review. Apply splits you judge correct; report changed ids for the dispatcher.

The foundational test: **"Can this doc change for more than one reason?"** If yes,
it is a split candidate.

---

## Procedure

1. List all docs and load each one:
   ```bash
   ldoc ls --json
   ldoc show <id>
   ```
2. Split-candidate signals:
   - Body has multiple `##` sections addressing distinct concerns (not sub-sections
     of one concern).
   - `history` has many entries with varied summaries (hot-file: many parties
     update for different reasons — see `20260615203928`).
   - Very long `requires` list pulling unrelated inputs.
   - Title uses "and" or contains a list ("X and Y", "A, B, C").
   - You would say "this doc owns X, but it also owns Y."
3. **Hot-file heuristic:** sort by history length; top candidates have ≥5
   entries with mixed-topic summaries.
4. For each split, decide new doc A/B (title, type, ownership), rewire plan,
   and whether the original becomes a signpost over A/B or is deprecated.
5. Apply each split:
   ```bash
   ldoc new --type <type> --title "<title>" --level <level> --status <status> --requires <dep-id,dep-id>
   ```
   Add `## Correction` to the original body (via `ldoc set <original-id> --body -`), then
   deprecate — two-part operation; `ldoc set` has no `--superseded-by`:
   ```bash
   ldoc set <original-id> --status deprecated
   ldoc link <original-id> --superseded-by <A-id>,<B-id>
   ldoc history <original-id> --add "garden-decompose: split into <A-id> and <B-id>"
   ```
   Rewire inbound edges (comma-separate multiple targets on edge flags):
   ```bash
   ldoc unlink <pointing-doc> --requires <original-id>
   ldoc link   <pointing-doc> --requires <A-id>
   ldoc history <pointing-doc> --add "garden-decompose: rewired requires after split"
   ```
6. **Edge reclassification:** after splits, move edges to `belongs_to` /
   `relates` / `requires` as appropriate (see garden dispatcher / edge vocabulary).

Do **not** run `cascade-check` here — the dispatcher unions changed ids and
cascades once at episode close.

---

## Output

```
garden — phase: decompose
Scanned: N docs
Findings:
  <id>  "<title>"  — <why split candidate>
Actions:
  [1] Split <id> into <A-id> + <B-id> …
Applied: [list]
Changed-ids: [id, …]
```
