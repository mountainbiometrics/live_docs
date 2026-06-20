---
name: reindex
description: >
  Rebuild the generated artifacts in docs/.index/ — the reverse-dependency map,
  hierarchy rollups, and orphan list. These files are DERIVED caches; they are
  never hand-edited and can always be regenerated from the flat docs/ store.
  Use after any bulk doc creation or deletion, after the garden skill splits or
  retires docs, or whenever docs/.index/ may be stale. Also run before
  cascade-check if you want a pre-built reverse-edge map on hand (though
  cascade-check recomputes its own fresh map regardless).
---

# reindex — Rebuild derived artifacts in docs/.index/

The files in `docs/.index/` are caches derived from the flat `docs/` store.
They are NEVER authoritative — the flat store is. If they conflict with
`docs/*.md` frontmatter, the frontmatter wins. Regenerate freely.

---

## How to run

```bash
# Canonical invocation via the porcelain CLI (preferred):
python3 scripts/ldoc.py reindex

# Or via the shell wrapper (resolves paths relative to itself):
.claude/skills/reindex/reindex.sh [docs_dir]

# Or call the shared script directly from the repo root:
python3 scripts/reindex.py [docs_dir]
```

`docs_dir` defaults to the configured docs store (`kb/02-docs/` in this repo) relative to the repo root.

The script creates the index dir (`<docs>/.index/`) if it doesn't exist, then writes:
- `<docs>/.index/dependents.json`
- `<docs>/.index/referenced_by.json`
- `<docs>/.index/hierarchy.md`

Orphan detection is NOT a reindex artifact. Orphan-hood is pure `belongs_to`
topology and is computed FRESH on demand via `python3 scripts/ldoc.py orphans`
(backed by `kb.orphans()`) — the single source of truth — rather than baked into
a stale `orphans.txt` cache.

---

## Artifacts

### dependents.json

Reverse hard-edge map: for each doc id, which OTHER doc ids list it in their
`requires` or `belongs_to` edges. Both are hard edges that cascade, so they are
combined into a single reverse map. Format:

```json
{
  "20260615090003": ["20260615100010", "20260615100011"],
  "20260615100003": [],
  ...
}
```

Every doc id present in the store appears as a key, even if its value is an
empty list. This lets callers check membership without a key-existence guard.

`provenance` edges (immutable derivation / source links) are navigation-only and
do NOT cascade; they get their own reverse map in `referenced_by.json` (same
format), which records for each doc which other docs cite it as provenance.

### hierarchy.md

A human-readable rollup of descendant-bearing docs and their children. The
signpost role is structural, not a type: for each doc that is the target of
`belongs_to` edges (regardless of its `type` — the `index` type is retired), list
every doc that has it as a `belongs_to` or `requires` target. Format:

```markdown
# live_docs Index Hierarchy
Generated: <ISO 8601 timestamp>

## <signpost doc title> (`<id>`)

| id | title | type | status |
|----|-------|------|--------|
| <id> | <title> | <type> | <status> |
...

---
```

Docs that no other doc depends on (no descendants) are omitted from this file.

### Orphans — NOT a reindex artifact

Orphan detection used to live here as `orphans.txt`. It does not anymore. A doc
is an orphan iff it has **no `belongs_to` edge in either direction** — no
`belongs_to` parent AND no `belongs_to` descendants — so it sits outside the
navigational hierarchy entirely. (`requires` / `relates` / `provenance` are NOT
hierarchy and do not count.) That is pure topology with no type exemptions in the
definition itself; consumers (garden, the viewer) apply their own judgment.

Because it is cheap, exact topology, it is computed FRESH on demand rather than
cached — query the single source of truth:
```bash
python3 scripts/ldoc.py orphans
```
This avoids the stale-cache hazard, consistent with how `cascade-check` uses
`ldoc neighbors` instead of reading `dependents.json`.

---

## Key facts about these artifacts

- **Rebuildable**: always. Delete `docs/.index/` entirely and rerun `reindex.py`.
- **Not hand-editable**: the comment `<!-- Generated ... do not hand-edit -->` in
  `hierarchy.md` signals this. Any manual edits will be overwritten on next run.
- **Not authoritative**: `cascade-check` (and any verification) should call
  `python3 scripts/ldoc.py neighbors <id> --json` (or `ldoc edges --json` for the
  full map) to get fresh data rather than reading `dependents.json` directly,
  to avoid stale-cache bugs. `dependents.json` is provided as a convenience for
  humans and other tools.
- **Safe to commit**: since they are generated from the flat store, committing them
  alongside doc changes gives reviewers a pre-computed view of the graph without
  requiring them to run the script.

## Implementation

Logic lives in `scripts/reindex.py` (imports `scripts/livedocs.py`).
The wrapper `.claude/skills/reindex/reindex.sh` calls it with an absolute path
resolved relative to the wrapper's own location, so it works from any CWD.
Stdlib only — no external dependencies.
