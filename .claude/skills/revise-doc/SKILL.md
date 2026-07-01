---
name: revise-doc
description: >
  Edit, update, revise, or amend an existing doc in the live_docs store with the
  same disciplined care that ingest-reference applies to new material. Performs a
  dedup/conflict scan before writing, classifies the change as substantive or
  provenance-only, appends a history entry and runs cascade-check only for
  substantive changes (title, body, type, level, status, requires, belongs_to),
  and validates the store afterward. Provenance/relates changes are never cascade
  edges; whether they get a history entry depends on intent: backfilling initial
  provenance is not history-worthy, but adding a genuinely new reference later is.
  Use whenever modifying the content, metadata, or edges of a doc that already
  exists in docs/.
---

# revise-doc — Governed edit of an existing doc (orchestrator)

The cardinal rule: **classify before you write.** A provenance-only change
(`provenance` or `relates` bookkeeping) never triggers cascade. Whether it needs a
history entry depends on intent: backfilling initial provenance is not
history-worthy, but adding a new reference later is. A substantive change
(anything that affects meaning, structure, or the dependency graph) requires
dedup/conflict checking, a history entry, and an impact pass.

This skill is a **thin orchestrator** with a **single-doc focus**. Its unique
parts are that classification gate and its history discipline; the shared phases
are composed from sub-skills — `identify-key-concepts`,
`map-concepts-to-docs` (as a dedup/conflict scan), and for substantive changes
`assess-blast-radius` + `cascade-check` and `synthesize-doc-changes`.

---

## You are the orchestrator — own the episode through to Step 7

You run this skill end to end. Each sub-skill it names (`identify-key-concepts`,
`map-concepts-to-docs`, …) runs **inline, in this same turn**, and its result
feeds the step after it — running a sub-skill is never where you stop.

- revise-doc captures the single `START` timestamp (Step 0) and emits the **one**
  review summary for the episode (Step 7), for substantive changes only. The
  sub-skills it runs do no episode bookkeeping of their own.
- If revise-doc is itself run as a step of a higher-level skill (e.g.
  `ingest-reference`), it does NOT emit a review summary — the outermost skill
  owns it (see Step 7).

---

## Step 0 — Capture the episode start time

```bash
date -u +%Y-%m-%dT%H:%M:%SZ
```

Record the literal timestamp it prints (e.g. `2026-06-19T23:48:00Z`); you'll paste this exact value into `review new --since` at the end of the episode.

Used at the end to generate a single review summary (substantive changes only —
see Step 7).

---

## Step 1 — Locate, load, and extract the concepts

1. The caller supplies either the doc **id** (e.g. `20260615090003`) or a
   **title fragment**. If a title fragment is given, resolve it:
   ```bash
   ldoc resolve "title fragment"
   ```
   If more than one id matches, `ldoc resolve` will error listing candidates — ask
   the caller to confirm. If the fragment is ambiguous, use `ldoc find`:
   ```bash
   ldoc find "title fragment" --json
   ```
2. Load the full doc — frontmatter, edges, and body:
   ```bash
   ldoc show <id>
   ```
3. State in plain language: (a) the doc's current content, and (b) exactly what
   the caller wants to change.
4. **Extract the concepts the revision introduces** — run **`/identify-key-concepts`**
   on the proposed change (don't stop after it; its concept list is the input to
   Step 2). A revision usually introduces just one or a few concepts:

   > Extract every distinct durable concept the revision introduces, labeled
   > `Concept`. For a small or purely corrective revision (typo, date, removing
   > stale text), a single concept entry suffices; for a revision adding
   > substantial new content or changing the doc's core claim, enumerate each
   > distinct concept separately. No splitting test.

   It returns the typed concept list (`Concept / Type / Asserts`) — these are the
   search keys for Step 2.

   If the revision is **provenance-only** (introduces no new concepts at all),
   skip this extraction and proceed to Step 4 directly.

---

## Step 2 — Dedup and conflict scan (invoke `map-concepts-to-docs`)

Run **`/map-concepts-to-docs`** with the concept list from Step 1. Emphasis: **a
dedup/conflict scan focused on the target doc's neighbors and same-type docs** —
does the revision duplicate or contradict an existing claim? It returns a
relationship verdict map. (Read-only.)

Act on the map before writing:

- **Duplication** — if the proposed content already lives, in substance, in
  another doc, prefer linking (`requires`/`relates`) or proposing a merge
  (surface to the user; do not merge silently) over editing this doc.
- **Conflict** — if the change contradicts a principle/decision/constraint/
  requirement elsewhere (`conflict-unresolved`), surface specifics and ask how
  to resolve. Do not apply the edit silently.

If neither duplication nor conflict is found, proceed.

---

## Step 3 — Apply the edit

Make the minimum change that satisfies the caller's intent. Prefer `ldoc` verbs
for all mutations; fall back to direct file editing only for body-text changes:

```bash
# scalar frontmatter fields
ldoc set <id> --title "New title"
ldoc set <id> --level preference --status target

# edge additions / removals
ldoc link <id> --requires <dep-id>
ldoc unlink <id> --requires <old-dep-id>
ldoc link <id> --belongs-to <parent-id>
ldoc link <id> --relates <peer-id>
ldoc link <id> --provenance <norm-id>
ldoc link <id> --superseded-by <new-id>

# body-text changes: edit docs/<id>.md directly (no ldoc verb for body in-place)
```

No gratuitous reformatting, no refactoring beyond scope. For a deprecation or a
wider rewrite that affects several docs at once, hand the plan to
`synthesize-doc-changes` rather than hand-writing each doc — it owns the
coherent-batch write discipline. Single-field edits stay inline here.

---

## Step 4 — Classify the change and act accordingly

This is the key decision gate.

### Provenance-only change
**Definition**: only `provenance` or `relates` fields changed (a provenance link
or see-also cluster link was added, removed, or reordered). No other frontmatter
field and no body content changed. Neither `provenance` nor `relates` is a cascade
edge.

**Action — decide on history based on intent**:

- **Backfilling initial provenance**: if you are retroactively recording the
  source a record was always derived from (e.g., one-time migration linking
  existing records to their origin), this is not a meaningful change.
  - Write the file.
  - Do NOT append a history entry.
  - Do NOT run cascade-check.

- **Adding a genuinely new provenance or relates link later**: if you are linking
  to a newly ingested source, a newly relevant reference, or a newly recognized
  peer cluster, this IS a change.
  - Record a history entry:
    ```bash
    ldoc history <id> --add "added provenance/relates: <label>"
    ```
  - Do NOT run cascade-check (provenance and relates are never cascade edges).

- **Bulk provenance cleanup**: apply all edits first, then run `validate` once at
  the end. No per-doc cascade needed. History entries are skipped if these are
  all backfills, or added if they are new references.

### Substantive change
**Definition**: any change to `title`, body content, `type`, `level`, `status`,
`requires`, `belongs_to`, or `tags`.

**Action — history entry first:**

```bash
ldoc history <id> --add "<concise description of what changed and why>"
```

**Action — assess impact, then cascade:**

For a substantive change you may first run **`/assess-blast-radius`** from this
doc's id to survey the impact set read-only before writing neighbors — useful
when the edit is large. Then run **`/cascade-check`** from this doc's id, passing
the change description as context. cascade-check runs its own two-pass model
(read-only walk, then batch write of `cascade` neighbors) and halts on
`incompatible`. (revise-doc owns the single episode summary — Step 7 — so the
cascade does not emit its own.)

Do not skip the cascade for substantive changes, even if the change seems
minor — cascade decides impact, not the editor.

---

## Step 5 — Validate the store

After writing all changes (including any cascade updates), confirm the store is
structurally sound:

```bash
ldoc validate
```

If `requires` or `belongs_to` edges were added or removed, also verify the edge map:
```bash
ldoc edges
```

Address any ERRORs before finishing. Surface WARNINGs to the user for review.

---

## Step 6 — Report

Emit a concise summary:

```
revise-doc — complete
Target: <id>  "<title>"
Change type: substantive | provenance-only

What changed:
  <one-line description>

History entry added: <yes / no>
  (if yes) at: <date>  summary: "<text>"

Cascade summary: <N neighbors evaluated — list each id: verdict>
  (or "skipped — provenance-only change")

Validation: <N docs scanned — clean | N errors, N warnings>
```

---

## Step 7 — Generate the review summary (substantive changes only; FINAL step)

**Only for substantive changes** (title, body, type, level, status, requires,
belongs_to, or tags were altered). Provenance-only changes that add no history
entry need no review summary — skip this step entirely for those.

**Standalone invocation only**: if revise-doc was called nested by a higher-level
skill (e.g. `ingest-reference`), do NOT emit a summary here — the top-level
skill owns the single summary for the episode. Emit one only when revise-doc is
the outermost skill for this editing session.

```bash
ldoc review new --since "2026-06-19T23:48:00Z"   # ← the literal value you recorded at the start
```

After it runs, confirm `touched` is non-empty and reflects the episode's changes.

Report the returned review id to the user:

```
Review summary created: <id>   (reviews/<id>.md)
```

Review is **post-hoc and non-gating** (see `review-is-post-hoc`): generating the
summary never blocks the change; it records the episode for later signoff.

---

## Frontmatter field reference

For reference during edits, the canonical frontmatter shape (field order is significant — serialize in this order):

| Field | Notes |
|-------|-------|
| `id` | Must match filename without `.md`. Never change. |
| `title` | Human-readable name. Substantive change if altered. |
| `label` | Short slug. |
| `type` | Enum: type, principle, goal, decision, constraint, requirement, use-case, guide, component, reference. Substantive change. |
| `status` | `living`, `target`, `deprecated`, or `reference`. Substantive change. |
| `level` | `incidental`, `trial`, `preference`, `requirement`. Substantive change. |
| `belongs_to` | List of parent doc ids — structural hierarchy; HARD/cascade edge. Substantive change if altered. Omit when empty. |
| `requires` | List of doc ids — existential cascade dependency; HARD edge. Substantive change if altered. Omit when empty. |
| `relates` | List of doc ids — symmetric clustering / see-also; NOT a cascade edge. Provenance-only if only this changes. Omit when empty. |
| `provenance` | List of source/reference doc ids — derivation; NOT a cascade edge. **Provenance-only** if only this changes. Omit when empty. |
| `superseded_by` | List of doc ids replacing this one. Required when `status: deprecated`. Omit when empty. |
| `tags` | `domain: []` and `scope: []`. Treat as substantive. Omit when both lists are empty. |
| `created` | ISO timestamp. Never change. |
| `history` | List of `{at, summary}`. Append only — never alter or delete existing entries. Omit when empty. |

---

## Common patterns

**Promote a level** (e.g. `trial` → `preference`): substantive — append history,
run cascade. The promotion may affect downstream docs that were waiting on the
level to stabilize.

**Deprecate a doc** (`status: living` or `target` → `status: deprecated`):
substantive — this is a two-part mandatory operation, not just a field change:
1. Add a `superseded_by` edge listing the doc(s) that replace this one:
   ```bash
   ldoc link <id> --superseded-by <new-id>
   ldoc set <id> --status deprecated
   ```
2. Add or update a `## Correction` section in the body explaining *why* the doc
   is wrong and which doc supersedes it. A bare status change with no
   `superseded_by` edge and no Correction section is **invalid**.
3. History entry must record the supersession. Run cascade from this doc:
   all `requires`/`belongs_to` dependents need to know their upstream is
   now deprecated. (For a deprecation that creates a replacement and rewrites
   several docs, hand the plan to `synthesize-doc-changes`.)

**Fix a typo in the body**: substantive (body changed) — but cascade will almost
certainly return all-`inconsequential` verdicts. Still run it.

**Add a `provenance` link**: provenance-only — no cascade. Add a history entry
only if it is a new reference (not a backfill of initial provenance).

**Add a `requires` or `belongs_to` edge**: substantive — this changes the graph
structure. Run cascade from both this doc and the newly-linked dependency.

**Add a `relates` link**: provenance-only — no cascade. Add a history entry only
if it is a new clustering link added after initial creation.

**Bulk provenance cleanup** (adding `provenance` links to many docs): apply all
edits first, then run `validate` once at the end. No per-doc cascade needed.

---

## Body-content rules

Doc bodies describe the **decision or mental model** — the claim the doc makes
about how things should be. They do NOT narrate implementation state, history, or
absence. Common anti-patterns to reject or correct before writing:

- Writing about absence ("X was never built", "summaries do not yet exist"):
  replace with the positive model ("summaries should exist") and let `status`
  (living vs target) carry the build gap.
- Migration plans or implementation details in the body ("a migration will
  happen", "this will be refactored"): these belong in a separate plan doc, not
  in the body of a living principle or decision.
- "Extension" or addendum notes that are really migration plans rather than
  corrections to the doc's own claim: strip them. If the doc's claim is itself
  wrong, write a `## Correction` section and deprecate the doc; if the claim is
  right but implementation lags, `status: target` is sufficient.

**Rule**: if implementation doesn't match the model, express the gap with
`status: target` — the body need not narrate it.
