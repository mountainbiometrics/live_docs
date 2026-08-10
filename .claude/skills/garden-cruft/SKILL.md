---
name: garden-cruft
user-invocable: false
description: >
  Gardening phase: remove cruft — strip dead implementation detail off
  still-current decisions (excavate), retype mis-typed docs, add missing whys,
  and delete refactor-chore docs whose durable why already lives elsewhere.
  Nested phase; garden dispatcher owns the episode and runs cruft early, before
  collapse merges things.
---

# garden-cruft — Remove cruft (atomicity phase)

**Contract:** nested phase only. Capture no START, run no `cascade-check`, emit
no review. Apply the verdicts you judge correct; report changed ids for the
dispatcher to union, cascade, and review once at episode close.

This phase is the executing **verb** for the cruft-removal principles: it is the
actor that performs the evaluative pass the store's principles call for but
nothing else carries out. The principles and the verdicts they imply live in the
shared file below — this phase only runs the sweep.

**Read and apply `.claude/skills/_shared/cruft-verdicts.md` verbatim** — it is
the single source of truth for cruft: the detection lens (what cruft looks like),
the refactor-plan pre-filter, the verdict vocabulary, their actions, and the
calibration learnings. Do **not** restate any of it here. This phase owns only
the *orchestration* of a sweep and the contract for *reporting* what it changed.

---

## Procedure

1. Load the candidate set (a cluster, a `scope`, or `ldoc ls --json` + `ldoc
   show <id>` for the full store).
2. Apply the shared file's detection lens and refactor-plan pre-filter, then
   assign each doc exactly one verdict from
   `.claude/skills/_shared/cruft-verdicts.md`.
3. Apply each verdict per that file's action guidance. When re-parenting or
   rewiring, read and apply `.claude/skills/_shared/belongs-to-placement.md`.
4. Report changed ids. Do **not** cascade, summarize, or review.

---

## Output

```
garden — phase: cruft
Scanned: N docs
Findings:
  <id>  "<title>"  — <verdict>: <why>
Actions:
  [1] EXCAVATE <id> — stripped <dead what>, kept the why
Applied: [list]
Changed-ids: [id, …]
```
