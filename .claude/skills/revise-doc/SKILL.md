---
name: revise-doc
description: >
  Edit, update, revise, or amend an existing doc in the live_docs store with the
  same disciplined care that ingest-reference applies to new material. Performs a
  dedup/conflict scan before writing, classifies the change as substantive or
  references-only, appends a history entry and runs cascade-check only for
  substantive changes (title, body, type, level, state, status, depends_on), and
  validates the store afterward. Reference/provenance changes are never cascade
  edges; whether they get a history entry depends on intent: backfilling initial
  provenance is not history-worthy, but adding a genuinely new reference later is.
  Use whenever modifying the content, metadata, or edges of a doc that already
  exists in docs/.
---

# revise-doc — Governed edit of an existing doc

The cardinal rule: **classify before you write.** A references-only change
(provenance bookkeeping) never triggers cascade. Whether it needs a history entry
depends on intent: backfilling initial provenance is not history-worthy, but
adding a new reference later is. A substantive change (anything that affects
meaning, structure, or the dependency graph) requires dedup/conflict checking,
a history entry, and a cascade-check pass.

---

## Step 1 — Locate and load the target doc

1. The caller supplies either the doc **id** (e.g. `20260615090003`) or a
   **title fragment**. If a title fragment is given, run:
   ```bash
   python3 scripts/edges.py --json
   ```
   Parse the `titles` map (`id → title`) and find the matching id. If more than
   one id matches, list the candidates and ask the caller to confirm.
2. Read `docs/<id>.md` in full — frontmatter and body.
3. State in plain language: (a) the doc's current content, and (b) exactly what
   the caller wants to change.

---

## Step 2 — Dedup and conflict scan (ingest-style care)

Before writing anything, check that the revision does not introduce redundancy or
contradiction.

**2a. Build the graph context:**
```bash
python3 scripts/edges.py --json
```
Note the doc's forward neighbors (`forward[id]`) and reverse neighbors
(`reverse[id]`). Surface any dangling edges reported in `dangling` to the user
before proceeding.

**2b. Read candidate docs** — the docs most likely to overlap with the revision:
- All forward neighbors (things this doc depends on).
- All reverse neighbors (things that depend on this doc).
- All docs of the same `type` (scan `titles` map; read any whose title or scope
  suggests overlap with the proposed change).

**2c. Evaluate for:**
- **Duplication** — does the proposed new content already live, in substance, in
  another doc? If so, prefer one of these resolutions instead of editing this doc:
  - **Link**: add the other doc to `depends_on` and note the relationship.
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

Make the minimum change that satisfies the caller's intent. Edit the target doc's
frontmatter fields and/or body — no gratuitous reformatting, no refactoring beyond
scope.

---

## Step 4 — Classify the change and act accordingly

This is the key decision gate.

### References-only change
**Definition**: only the `references` field changed (a provenance link was added,
removed, or reordered). No other frontmatter field and no body content changed.

**Action — decide on history based on intent**:

- **Backfilling initial provenance**: if you are retroactively recording the
  source a record was always derived from (e.g., one-time migration linking
  existing records to their origin), this is not a meaningful change.
  - Write the file.
  - Do NOT append a history entry.
  - Do NOT run cascade-check.

- **Adding a genuinely new reference later**: if you are linking to a newly
  ingested source or a newly relevant reference, this IS a change.
  - Append a history entry: `summary: "added reference: <label>"` (or similar).
  - Write the file.
  - Do NOT run cascade-check (reference links are never cascade edges).

- **Bulk provenance cleanup**: apply all edits first, then run `validate` once at
  the end. No per-doc cascade needed. History entries are skipped if these are
  all backfills, or added if they are new references.

### Substantive change
**Definition**: any change to `title`, body content, `type`, `level`, `state`,
`status`, or `depends_on`.

**Action — history entry first:**

Append to the doc's `history` list:
```yaml
- at: "<today's date ISO 8601, e.g. 2026-06-15>"
  summary: "<concise description of what changed and why>"
```
If `history:` is currently `history: []`, replace it with block-sequence form:
```yaml
history:
  - at: "<date>"
    summary: "<description>"
```

**Action — cascade-check next:**

Invoke the `cascade-check` skill starting from this doc's id. Provide the change
description as context. The skill will:
- Walk both upstream (`forward`) and downstream (`reverse`) neighbors.
- Emit a verdict (`inconsequential`, `cascade`, `incompatible`, or
  `context-request`) for each neighbor.
- Update any neighbors that receive a `cascade` verdict (appending their own
  history entries).
- Halt and surface `incompatible` branches to the user.

Do not skip cascade-check for substantive changes, even if the change seems
minor — cascade decides impact, not the editor.

---

## Step 5 — Validate the store

After writing all changes (including any cascade updates), confirm the store is
structurally sound:

```bash
python3 scripts/validate.py
```

If `depends_on` edges were added or removed, also run:
```bash
python3 scripts/edges.py
```

Address any ERRORs before finishing. Surface WARNINGs to the user for review.

---

## Step 6 — Report

Emit a concise summary:

```
revise-doc — complete
Target: <id>  "<title>"
Change type: substantive | references-only

What changed:
  <one-line description>

History entry added: <yes / no>
  (if yes) at: <date>  summary: "<text>"

Cascade summary: <N neighbors evaluated — list each id: verdict>
  (or "skipped — references-only change")

Validation: <N docs scanned — clean | N errors, N warnings>
```

---

## Frontmatter field reference

For reference during edits, the canonical frontmatter shape:

| Field | Notes |
|-------|-------|
| `id` | Must match filename without `.md`. Never change. |
| `title` | Human-readable name. Substantive change if altered. |
| `type` | Enum: type, principle, goal, decision, constraint, requirement, use-case, guide, component, reference, index. Substantive change. |
| `status` | `living` or `historical`. Substantive change. |
| `level` | `incidental`, `trial`, `preference`, `requirement`. Substantive change. |
| `state` | `actual` or `target`. Substantive change. |
| `depends_on` | List of doc ids — STRUCTURAL/cascade edges. Substantive change if altered. |
| `references` | List of provenance links — NOT cascade edges. **References-only** if only this changes. |
| `tags` | `domain: []` and `scope: []`. Treat as substantive. |
| `created` | ISO timestamp. Never change. |
| `history` | List of `{at, summary}`. Append only — never alter or delete existing entries. |

---

## Common patterns

**Promote a level** (e.g. `trial` → `preference`): substantive — append history,
run cascade. The promotion may affect downstream docs that were waiting on the
level to stabilize.

**Retire a doc** (`status: living` → `status: historical`): substantive — history
entry must say which doc supersedes this one. Run cascade: all dependents need to
know their upstream is now historical.

**Fix a typo in the body**: substantive (body changed) — but cascade will almost
certainly return all-`inconsequential` verdicts. Still run it.

**Add a `references` link**: references-only — no cascade. Add a history entry
only if it is a new reference (not a backfill of initial provenance).

**Add a `depends_on` edge**: substantive — this changes the graph structure. Run
cascade from both this doc and the newly-linked dependency.

**Bulk provenance cleanup** (adding `references` links to many docs): apply all
edits first, then run `validate` once at the end. No per-doc cascade needed.
