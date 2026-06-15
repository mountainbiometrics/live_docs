---
name: validate
description: >
  Read-only mechanical check of the entire docs/ store. Verifies every doc has
  required fields with valid enum values, that id matches filename, that all
  depends_on references resolve, and that reference docs have their extra fields.
  Empty history: [] is valid and normal. Emits a report but does NOT fix anything.
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
# From any directory — wrapper resolves paths relative to itself:
.claude/skills/validate/validate.sh [docs_dir]

# Or call the shared script directly from the repo root:
python3 scripts/validate.py [docs_dir]
```

`docs_dir` defaults to `docs/` relative to the repo root. The script exits with
code 0 if no violations are found, 1 otherwise.

---

## Checks performed

### 1. Required baseline fields

Every doc must have all of: `id`, `title`, `type`, `status`, `level`, `state`,
`depends_on`, `tags` (with `domain` and `scope` sub-keys), `created`, `history`.

Missing any field → **ERROR: missing field `<field>` in `<id>`**.

### 2. Valid enum values

| Field | Valid values |
|-------|-------------|
| `type` | type, principle, goal, decision, constraint, requirement, use-case, guide, component, reference, index |
| `status` | living, historical |
| `level` | incidental, trial, preference, requirement |
| `state` | actual, target |

Out-of-enum value → **ERROR: invalid `<field>` value `<value>` in `<id>`**.

### 3. id == filename

The `id` in frontmatter must equal the filename without `.md` extension.
Mismatch → **ERROR: id/filename mismatch in `<filename>`** (frontmatter says
`<id>`, filename is `<filename>`).

### 4. depends_on resolution

Every id listed in any doc's `depends_on` must correspond to an existing
`docs/<dep_id>.md` file. Broken ref → **ERROR: broken depends_on `<dep_id>` in
`<id>`**.

### 5. Reference doc extras

Docs with `type: reference` must also have `kind`, `source`, and `imported`
fields. `kind` must be one of: brainstorm, plan, clipping, external.
Missing or invalid → **ERROR: reference doc `<id>` missing/invalid `<field>`**.

### 6. Provenance rule

A doc that has no `source` derivation (i.e., not a reference doc and has an
empty `depends_on`) and `level` higher than `incidental` is flagged.
Rationale: if a doc makes a strong claim (trial/preference/requirement) but cites
no prior doc as evidence or basis, its provenance is suspect — it may have
calcified without a conscious decision.
→ **WARNING: `<id>` has level `<level>` but empty depends_on (no provenance)**.
This is a warning, not an error; some docs (roots, axioms) legitimately have no
dependencies.

### 7. History (no check)

`history: []` is valid and normal. History records only genuine changes applied
after doc creation; newly created docs start with an empty list. No error is
emitted for an empty or absent history block.

---

## Output format

```
validate — docs/
Scanned: N docs

ERRORS (must fix):
  [E] 20260615090003  missing field `level`
  [E] 20260615100001  broken depends_on `20260615999999`
  [E] 20260615090009  reference doc missing `imported`

WARNINGS (should review):
  [W] 20260615100004  level `requirement` but depends_on is empty (no provenance)

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
