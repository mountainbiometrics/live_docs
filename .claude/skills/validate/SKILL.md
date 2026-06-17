---
name: validate
description: >
  Read-only mechanical check of the entire docs/ store. Verifies every doc has
  required fields with valid enum values, that id matches filename, that all
  requires/belongs_to references resolve, that deprecated docs have a superseded_by
  edge, and that reference docs have their extra fields. Omitted edge lists and
  omitted history are valid and normal. Emits a report but does NOT fix anything.
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

### 2. Valid enum values

| Field | Valid values |
|-------|-------------|
| `type` | type, principle, goal, decision, constraint, requirement, use-case, guide, component, reference, index |
| `status` | living, target, deprecated, reference |
| `level` | incidental, trial, preference, requirement |

Note: `state` has been removed from the schema. A doc with `state:` present
should be flagged → **WARNING: `<id>` has stale `state` field (removed from
schema; fold into `status`)**.

Out-of-enum value → **ERROR: invalid `<field>` value `<value>` in `<id>`**.

### 3. id == filename

The `id` in frontmatter must equal the filename without `.md` extension.
Mismatch → **ERROR: id/filename mismatch in `<filename>`** (frontmatter says
`<id>`, filename is `<filename>`).

### 4. Edge resolution

Every id listed in any doc's `requires`, `belongs_to`, `relates`, `provenance`,
or `superseded_by` must correspond to an existing `docs/<dep_id>.md` file.
Broken ref → **ERROR: broken `<field>` edge `<dep_id>` in `<id>`**.

### 5. Reference doc extras

Docs with `type: reference` must also have `kind`, `source`, and `imported`
fields. `kind` must be one of: brainstorm, plan, clipping, external.
Missing or invalid → **ERROR: reference doc `<id>` missing/invalid `<field>`**.

### 6. Deprecated docs must have superseded_by

A doc with `status: deprecated` must have a non-empty `superseded_by` edge list.
Missing it → **ERROR: deprecated doc `<id>` has no `superseded_by` edge**.

Rationale: deprecation without a successor edge is a dead end in the graph.
Callers and dependents cannot discover what replaced this doc.

### 7. Provenance rule

A doc that is not a reference doc and has both empty `requires` and empty
`belongs_to`, and `level` higher than `incidental`, is flagged.
Rationale: if a doc makes a strong claim (trial/preference/requirement) but has
no hard upstream edge, its provenance is suspect — it may have calcified without
a conscious decision.
→ **WARNING: `<id>` has level `<level>` but no requires/belongs_to edges (no
provenance)**.
This is a warning, not an error; some docs (roots, axioms) legitimately have no
dependencies.

### 8. History and edge lists (no check for emptiness)

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

WARNINGS (should review):
  [W] 20260615100004  level `requirement` but no requires/belongs_to edges (no provenance)
  [W] 20260615110005  stale `state` field (removed from schema; fold into `status`)

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
