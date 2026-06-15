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
# From any directory — wrapper resolves paths relative to itself:
.claude/skills/reindex/reindex.sh [docs_dir]

# Or call the shared script directly from the repo root:
python3 scripts/reindex.py [docs_dir]
```

`docs_dir` defaults to `docs/` relative to the repo root.

The script creates `docs/.index/` if it doesn't exist, then writes:
- `docs/.index/dependents.json`
- `docs/.index/hierarchy.md`
- `docs/.index/orphans.txt`

---

## Artifacts

### dependents.json

Reverse-dependency map: for each doc id, which OTHER doc ids list it in their
`depends_on`. Format:

```json
{
  "20260615090003": ["20260615100010", "20260615100011"],
  "20260615100003": [],
  ...
}
```

Every doc id present in the store appears as a key, even if its value is an
empty list. This lets callers check membership without a key-existence guard.

### hierarchy.md

A human-readable rollup of `index` docs and their children. For each doc of
`type: index`, list every doc that `depends_on` it. Format:

```markdown
# live_docs Index Hierarchy
Generated: <ISO 8601 timestamp>

## <index doc title> (`<id>`)

| id | title | type | status |
|----|-------|------|--------|
| <id> | <title> | <type> | <status> |
...

---
```

Docs that do not depend on any index doc are omitted from this file (they may
appear in `orphans.txt` instead).

### orphans.txt

One id per line: docs with NO inbound depends_on edges (nothing depends on them)
AND NO outbound depends_on edges (they depend on nothing). These are structural
orphans — disconnected from the graph entirely.

Exempt from orphan reporting:
- Docs of `type: index` (they are roots by design).
- Docs of `type: type` (they define vocabulary; they anchor the graph but are
  rarely cited by other docs).

Format:
```
# orphans — docs with no graph edges
# Generated: <timestamp>
# These docs are disconnected from the dependency graph.
# Consider: add edges, or retire to status: historical.
20260615XXXXXX
20260615YYYYYY
```

---

## Key facts about these artifacts

- **Rebuildable**: always. Delete `docs/.index/` entirely and rerun `reindex.py`.
- **Not hand-editable**: the comment `<!-- Generated ... do not hand-edit -->` in
  `hierarchy.md` signals this. Any manual edits will be overwritten on next run.
- **Not authoritative**: `cascade-check` (and any verification) should call
  `python3 scripts/edges.py --json` to get fresh forward/reverse maps rather than
  reading `dependents.json` directly, to avoid stale-cache bugs.
  `dependents.json` is provided as a convenience for humans and other tools.
- **Safe to commit**: since they are generated from the flat store, committing them
  alongside doc changes gives reviewers a pre-computed view of the graph without
  requiring them to run the script.

## Implementation

Logic lives in `scripts/reindex.py` (imports `scripts/livedocs.py`).
The wrapper `.claude/skills/reindex/reindex.sh` calls it with an absolute path
resolved relative to the wrapper's own location, so it works from any CWD.
Stdlib only — no external dependencies.
