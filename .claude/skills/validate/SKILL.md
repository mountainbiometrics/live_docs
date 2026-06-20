---
name: validate
description: >
  Read-only mechanical check of the entire docs/ store. Verifies every doc has
  required fields with valid enum values, that labels are trimmed and unique, that
  all requires/belongs_to/relates/provenance references resolve, that `belongs_to`
  is acyclic, that deprecated docs have a superseded_by edge, that reference docs
  have their extra fields, and that every doc carries a summary. Omitted edge lists
  and omitted history are valid and normal. Emits a report but does NOT fix anything.
  Use before a release, after bulk edits, or anytime you want confidence the store
  is structurally sound. To also get fix proposals, use the garden `consistency`
  pass instead.
---

# validate — Read-only structural integrity check

Validate is purely diagnostic. It reads, checks, and reports. It never modifies
any file. For fixes, use `garden consistency`.

---

## How to run

```bash
# Canonical invocation via the porcelain CLI (preferred):
python3 scripts/ldoc.py validate

# Or via the shell wrapper (resolves paths relative to itself):
.claude/skills/validate/validate.sh [docs_dir]

# Or call the shared script directly from the repo root:
python3 scripts/validate.py [docs_dir]
```

`docs_dir` defaults to `docs/` relative to the repo root. The script exits with
code 0 if no violations are found, 1 otherwise.

---

## Checks performed

### 1. Required baseline fields

Every doc must have all of: `id`, `title`, `label`, `type`, `status`, `level`,
`created`.

Edge lists (`belongs_to`, `requires`, `relates`, `provenance`, `superseded_by`),
`tags`, and `history` are optional — absent means empty and that is **valid**.
No error is emitted for missing optional fields.

Missing any required field → **ERROR: missing field `<field>` in `<id>`**.

### 2. Label well-formed and unique

`label` must be trimmed (no leading or trailing whitespace) →
**ERROR: `<id>` label has leading/trailing whitespace**.

`label` must be unique across the store; two docs sharing a label is an error →
**ERROR: duplicate label `<label>` in `<id>` (also in `<other_id>`)**.

### 3. Valid enum values

| Field | Valid values |
|-------|-------------|
| `type` | type, principle, goal, decision, constraint, requirement, use-case, guide, component, reference |
| `status` | living, target, deprecated, reference |
| `level` | incidental, trial, preference, requirement |

`type` no longer includes `index`.

`domain` must be a list when present →
**ERROR: `<id>` field `domain` must be a list**.

Out-of-enum value → **ERROR: invalid `<field>` value `<value>` in `<id>`**.

### 4. Edge resolution

Every id listed in any doc's `requires`, `belongs_to`, `relates`, or
`superseded_by` must correspond to an existing `docs/<dep_id>.md` file.
Broken ref → **ERROR: broken `<field>` edge `<dep_id>` in `<id>`**.

`provenance` ids must likewise resolve, but an unresolved provenance ref is a
**WARNING**, not an error → **WARNING: unresolved `provenance` ref `<ref_id>`
in `<id>`**.

### 5. Acyclicity — `belongs_to` ONLY

Acyclicity is enforced on **`belongs_to` only** (`DAG_EDGE_FIELDS =
("belongs_to",)`). `belongs_to` is the scope/lineage DAG that the
effective-scope walk depends on, so a cycle there is a hard structural error.
A cycle → **ERROR: cycle detected in `belongs_to` graph:
`<id>` → … → `<id>`**.

`requires` is **not** enforced acyclic — two decisions can mutually depend on
each other (each moot without the other), which is legitimate and not
load-ordered like code. `relates` is symmetric "see-also", so cycles are
normal there too. Neither is checked for cycles.

### 6. Reference doc extras

Docs with `type: reference` must also have `kind`, `source`, and `imported`
fields. `kind` must be one of: brainstorm, plan, clipping, external.
Missing or invalid → **ERROR: reference doc `<id>` missing/invalid `<field>`**.

### 7. Deprecated docs must have superseded_by

A doc with `status: deprecated` must have a non-empty `superseded_by` edge list.
Missing it → **ERROR: deprecated doc `<id>` has no `superseded_by` edge**.

Rationale: deprecation without a successor edge is a dead end in the graph.
Callers and dependents cannot discover what replaced this doc.

### 8. Summary presence and length

Every doc must carry a non-empty `summary` →
**ERROR: `<id>` has no `summary`**.

The summary is a tight signpost. A summary running long (beyond roughly 60
words) is flagged as a guideline violation →
**WARNING: `<id>` summary is long (~<N> words); tighten to a signpost**.

### 9. History and edge lists (no check for emptiness)

History (`history`) and all edge lists (`requires`, `belongs_to`, `relates`,
`provenance`, `superseded_by`) are optional. Absent or empty means nothing is
recorded — that is **valid and normal**. No error is emitted for absent or empty
optional fields. Do not write `[]` for empty lists; omit the field entirely.

---

## Output format

```
validate — docs/
Scanned: N docs

ERRORS (must fix):
  [E] 20260615090003  missing field `level`
  [E] 20260615100001  broken `requires` edge `20260615999999`
  [E] 20260615090009  reference doc missing `imported`
  [E] 20260615110002  deprecated doc has no `superseded_by` edge
  [E] 20260615090007  cycle detected in `belongs_to` graph
  [E] 20260615090008  has no `summary`

WARNINGS (should review):
  [W] 20260615100004  unresolved `provenance` ref `20260615999998`
  [W] 20260615110005  summary is long (~84 words); tighten to a signpost

Summary: N errors, N warnings
Exit code: 1 (errors present)
```

If clean:
```
validate — docs/
Scanned: N docs
All checks passed.
Exit code: 0
```

---

## Implementation

Logic lives in `scripts/validate.py` (imports `scripts/livedocs.py`).
The wrapper `.claude/skills/validate/validate.sh` calls it with an absolute path
resolved relative to the wrapper's own location, so it works from any CWD.
Stdlib only — no external dependencies.
