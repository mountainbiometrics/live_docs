---
name: garden
description: >
  Periodic maintenance: thin dispatcher over garden-* phase sub-skills
  (atomicity, structure, form). Owns the episode — one START, routing, one
  cascade over the union of changes, one review. Use for decomposition, drift
  repair, orphan homes, duplicate cleanup, surface-quality sampling, or on a
  schedule. Invoke with natural-language intent (/garden clean up duplicates) or
  /garden all for a full sweep.
---

# garden — Dispatcher over gardening phases

Gardening is a **thin dispatcher** over single-purpose phases. You own the **whole episode**; phases report changed ids only.

**Three axes:**
- **Atomicity** — `garden-cruft`, `garden-decompose`, `garden-collapse`
- **Structure** — `garden-hierarchy`, `garden-domains`, `garden-densify`, `garden-summarize`
- **Form** — `garden-refine`, `garden-integrity`

Phases are `user-invocable: false` — invoke them via the Skill tool, never tell
the user to run them directly.

---

## Episode start (always first)

```bash
date -u +%Y-%m-%dT%H:%M:%SZ
```

Record the literal timestamp for `ldoc review new --since` at episode close.

---

## Routing

### `/garden` (no arg) — triage + route

Cheap read-only scan; run the phase(s) the store most needs; if nothing glares,
sample 1–2 maintenance phases.

| Signal | Route |
|--------|-------|
| `ldoc orphans` count high (living atomic orphans) | `garden-hierarchy` |
| Signpost with ≳12 direct children | `garden-hierarchy` (re-scope) |
| `ldoc validate` errors | `garden-integrity` |
| Docs naming dead symbols / refactor-chore docs / what-without-why | `garden-cruft` |
| Hot-files (history ≥5, mixed summaries) | `garden-decompose` |
| Near-duplicate titles/summaries (skim `ldoc ls`) | `garden-collapse` |
| Cluster under-linked / prose `[[id]]` mentions aren't edges / cascade can't reach related docs | `garden-densify` |
| Staleness (dependency updated after dependent) | **signal only** — note for user; cascade-check owns writes |
| else | random 1–2 of `{refine, domains, decompose}` |

### `/garden <natural-language intent>`

The dispatcher **reasons** from arbitrary natural-language intent to the
appropriate phase(s) — do not treat these as a fixed lookup table. Any intent
not listed here still has a nearest phase; infer it. When intent spans axes,
chain the relevant phases; still one episode.

Illustrative examples:
- "clean up duplicates" / "merge duplicates" → `garden-collapse`
- "remove cruft" / "excavate dead implementation" / "strip stale symbol names" / "drop refactor-chore docs" → `garden-cruft`
- "find homes for orphans" / "grouping" / "hierarchy" → `garden-hierarchy`
- "fix cut-off titles" / "surface quality" / "keywords" → `garden-refine`
- "split overloaded" / "decompose" → `garden-decompose`
- "domain tags" → `garden-domains`
- "densify edges" / "build missing edges" / "materialize wikilinks" / "make cascade reach related docs" → `garden-densify`
- "validate fixes" / "broken edges" → `garden-integrity`
- "refresh signpost summaries" → `garden-summarize` (on named signposts)

**Dispatcher honesty.** Every phase does one job; the union of jobs is finite. If
an intent has **no** fitting phase, say so — "I have no phase for that intent" —
rather than silently routing it to an adjacent phase that does something
tangential (or nothing). Naming the gap is the correct answer; a wrong route is
not. (Note: *building `requires`/`relates` edges* — semantic densification — now
has a home in `garden-densify`; route it there, not to `garden-hierarchy`
placement or `garden-domains` tagging as a near-miss.)

### `/garden all` — full sweep (dependency order)

Phase skills (in order):

```
cruft → decompose → collapse → hierarchy → domains → densify → refine → integrity
```

**Cruft runs first.** REMOVE/EXCAVATE should fire **before** decompose splits and
before collapse merges: there is no point splitting a doc about to be excavated,
or merging one about to be removed — and excavating first means collapse dedups
the distilled survivors, not the crusted originals. This extends the antagonist
ordering (decompose-before-collapse): purge and excavate, *then* split, *then*
merge.

**Densify runs after structure is settled, before form.** Edges should be built
once the docs they connect have stopped moving — splitting, merging, and
re-homing all change which docs and parents exist, so densifying earlier would
wire edges to docs about to change or vanish. Running it after `hierarchy` and
`domains` connects the *final* set of docs; running it before `refine` and
`integrity` means the new edges still get the form pass and the mechanical
ref-integrity check.

Then **dispatcher steps** (not separate user-invocable phases):

1. **Summarize once** — union `Signposts-changed` from `garden-hierarchy` (and any
   signpost that gained/lost members from collapse fold). Invoke `garden-summarize`
   on each id **once**, after all structure/form phases so guides reflect final
   membership. Do not summarize inside `garden-hierarchy`.
2. **Cascade-check** — from `EPISODE_CHANGED`. Re-run `garden-summarize` only for
   signposts newly flagged by the descendant-summary rule that were **not** already
   summarized in step 1 (or whose members changed again during cascade writes).

Atomicity before structure so homes reflect final docs.

---

## Running a phase

Invoke the matching `garden-*` skill. Each phase returns:

```
Changed-ids: [id, …]
```

`garden-hierarchy` also returns `Signposts-changed: [signpost-id, …]`. Collect
these into `SIGNPOSTS_TO_SUMMARIZE` for the pre-cascade summarize pass.

**Union** all changed ids across phases into `EPISODE_CHANGED`.

Phases must **not** capture START, run cascade, or emit review.

---

## Episode close (only if anything wrote)

If `EPISODE_CHANGED` is empty, emit **no review** and stop.

Otherwise:

1. **Summarize signposts** (if `SIGNPOSTS_TO_SUMMARIZE` non-empty, or hierarchy
   ran in this episode): invoke `garden-summarize` once per signpost id in the
   union. Skip ids already summarized this episode unless a later phase changed
   their members again.
2. **One cascade-check** from the union of changed ids (nested — no review from
   cascade). Resolve verdicts; re-run `garden-summarize` only on signposts flagged
   by the descendant-summary rule that were not already summarized in step 1.
3. **Validate:**
   ```bash
   ldoc validate
   ```
4. **One review:**
   ```bash
   ldoc review new --since "<START>"
   ```
5. Report review id. Note if `hierarchy.md` needs `ldoc reindex`.

Review is post-hoc and non-gating: every change is blessed on creation; the review layer challenges changes after the fact, not before.

---

## Apply-and-review discipline

Phases apply judgment directly; correctness is caught by the review summary, not
a pre-write gate. Deprecations/merges need `## Correction` + history entries.
