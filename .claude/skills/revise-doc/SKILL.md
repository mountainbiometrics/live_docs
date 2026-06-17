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

# revise-doc — Governed edit of an existing doc

The cardinal rule: **classify before you write.** A provenance-only change
(`provenance` or `relates` bookkeeping) never triggers cascade. Whether it needs a
history entry depends on intent: backfilling initial provenance is not
history-worthy, but adding a new reference later is. A substantive change
(anything that affects meaning, structure, or the dependency graph) requires
dedup/conflict checking, a history entry, and a cascade-check pass.

---

## Step 0 — Capture the episode start time

Before doing anything else, record the current UTC time:

```bash
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

This timestamp will be used at the end of the episode to generate a single
review summary (for substantive changes only — see Step 7).

---

## Step 1 — Locate and load the target doc

1. The caller supplies either the doc **id** (e.g. `20260615090003`) or a
   **title fragment**. If a title fragment is given, resolve it:
   ```bash
   python3 scripts/ldoc.py resolve "title fragment"
   ```
   If more than one id matches, `ldoc resolve` will error listing candidates — ask
   the caller to confirm. If the fragment is ambiguous, use `ldoc find`:
   ```bash
   python3 scripts/ldoc.py find "title fragment" --json
   ```
2. Load the full doc — frontmatter, edges, and body:
   ```bash
   python3 scripts/ldoc.py show <id>
   ```
3. State in plain language: (a) the doc's current content, and (b) exactly what
   the caller wants to change.

---

## Step 2 — Dedup and conflict scan (ingest-style care)

Before writing anything, check that the revision does not introduce redundancy or
contradiction.

**2a. Build the graph context:**
```bash
python3 scripts/ldoc.py neighbors <id> --json
```
Note the `requires`/`belongs_to` entries (upstream) and `dependents` entries (downstream).
To check for dangling edges across the store, run `ldoc edges --json` and inspect
the `dangling` key — surface any to the user before proceeding.

**2b. Read candidate docs** — the docs most likely to overlap with the revision:
- All upstream neighbors (things this doc depends on): from `ldoc neighbors` output.
- All downstream neighbors (things that depend on this doc): from `ldoc neighbors` output.
- All docs of the same `type`:
  ```bash
  python3 scripts/ldoc.py ls --type <type> --json
  ```
  Read any whose title or scope suggests overlap with the proposed change via
  `ldoc show <candidate-id>`.

**2c. Evaluate for:**
- **Duplication** — does the proposed new content already live, in substance, in
  another doc? If so, prefer one of these resolutions instead of editing this doc:
  - **Link**: add the other doc to `requires` or `relates` (whichever fits the
    relationship) and note the relationship.
  - **Merge**: propose consolidating the two docs (surface to user; do not merge
    silently).
  Surface the overlapping doc id and title, explain the overlap, and ask how to
  proceed.
- **Conflict** — does the proposed change contradict a principle, decision,
  constraint, or requirement in another doc? If so, surface the conflict with
  specifics and ask how to resolve it. Do not apply the edit silently.

If neither duplication nor conflict is found, proceed.

---

## Step 3 — Apply the edit

Make the minimum change that satisfies the caller's intent. Prefer `ldoc` verbs
for all mutations; fall back to direct file editing only for body-text changes:

```bash
# scalar frontmatter fields
python3 scripts/ldoc.py set <id> --title "New title"
python3 scripts/ldoc.py set <id> --level preference --status target

# edge additions / removals
python3 scripts/ldoc.py link <id> --requires <dep-id>
python3 scripts/ldoc.py unlink <id> --requires <old-dep-id>
python3 scripts/ldoc.py link <id> --belongs-to <parent-id>
python3 scripts/ldoc.py link <id> --relates <peer-id>
python3 scripts/ldoc.py link <id> --provenance <norm-id>
python3 scripts/ldoc.py link <id> --superseded-by <new-id>

# body-text changes: edit docs/<id>.md directly (no ldoc verb for body in-place)
```

No gratuitous reformatting, no refactoring beyond scope.

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
    python3 scripts/ldoc.py history <id> --add "added provenance/relates: <label>"
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
python3 scripts/ldoc.py history <id> --add "<concise description of what changed and why>"
```

**Action — cascade-check next:**

Invoke the `cascade-check` skill starting from this doc's id. Provide the change
description as context. The skill will:
- Walk both upstream (`requires`/`belongs_to`) and downstream (`dependents`)
  neighbors via `ldoc neighbors`.
- Emit a verdict (`inconsequential`, `cascade`, `incompatible`, or
  `context-request`) for each neighbor.
- Update any neighbors that receive a `cascade` verdict using `ldoc set`/`ldoc link`
  and `ldoc history`.
- Halt and surface `incompatible` branches to the user.

Do not skip cascade-check for substantive changes, even if the change seems
minor — cascade decides impact, not the editor.

---

## Step 5 — Validate the store

After writing all changes (including any cascade updates), confirm the store is
structurally sound:

```bash
python3 scripts/ldoc.py validate
```

If `requires` or `belongs_to` edges were added or removed, also verify the edge map:
```bash
python3 scripts/ldoc.py edges
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

Review is **post-hoc and non-gating** (see `review-is-post-hoc`): generating
the summary never blocks the change; it records the episode for later
review/signoff.

**Standalone invocation only**: if revise-doc was called by a higher-level
skill (e.g. `ingest-reference`), do NOT emit a summary here — the top-level
skill owns the single summary for the episode. Emit a summary only when
revise-doc is the outermost skill for this editing session.

```bash
python3 scripts/ldoc.py review new --since "$START"
```

Report the returned review id to the user:

```
Review summary created: <id>   (reviews/<id>.md)
```

---

## Frontmatter field reference

For reference during edits, the canonical frontmatter shape (field order is significant — serialize in this order):

| Field | Notes |
|-------|-------|
| `id` | Must match filename without `.md`. Never change. |
| `title` | Human-readable name. Substantive change if altered. |
| `label` | Short slug. |
| `type` | Enum: type, principle, goal, decision, constraint, requirement, use-case, guide, component, reference, index. Substantive change. |
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
   python3 scripts/ldoc.py link <id> --superseded-by <new-id>
   python3 scripts/ldoc.py set <id> --status deprecated
   ```
2. Add or update a `## Correction` section in the body explaining *why* the doc
   is wrong and which doc supersedes it. A bare status change with no
   `superseded_by` edge and no Correction section is **invalid**.
3. History entry must record the supersession. Run cascade from this doc:
   all `requires`/`belongs_to` dependents need to know their upstream is
   now deprecated.

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
