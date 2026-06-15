#!/usr/bin/env python3
"""
reindex.py — Rebuild generated artifacts in docs/.index/.

Usage:
    python scripts/reindex.py [docs_dir]

docs_dir defaults to DOCS_DIR from livedocs (repo root / docs).

Generates:
    docs/.index/dependents.json   — reverse-dependency map
    docs/.index/hierarchy.md      — index doc children rollup
    docs/.index/orphans.txt       — disconnected docs

Stdlib only. No external dependencies.
These files are DERIVED. Never hand-edit them; rerun this script instead.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure scripts/ is on sys.path so livedocs is importable from any CWD
sys.path.insert(0, str(Path(__file__).resolve().parent))

from livedocs import DOCS_DIR, load_all, forward_edges, reverse_edges


# ---------------------------------------------------------------------------
# Types exempt from orphan detection (graph roots by design)
# ---------------------------------------------------------------------------

ORPHAN_EXEMPT_TYPES = {"index", "type"}


# ---------------------------------------------------------------------------
# Generate dependents.json
# ---------------------------------------------------------------------------

def write_dependents_json(rev: dict, index_dir: Path) -> None:
    """Write reverse-dependency map to dependents.json."""
    output = {k: sorted(v) for k, v in sorted(rev.items())}
    out_path = index_dir / "dependents.json"
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"  wrote {out_path}")


# ---------------------------------------------------------------------------
# Generate hierarchy.md
# ---------------------------------------------------------------------------

def write_hierarchy_md(docs: dict, fwd: dict, index_dir: Path) -> None:
    """Write index-doc hierarchy rollup to hierarchy.md."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    index_docs = [d for d in docs.values() if d.get("type") == "index"]
    index_docs.sort(key=lambda d: d["id"])

    lines = [
        "# live_docs Index Hierarchy",
        f"<!-- Generated: {now} — do not hand-edit. Run reindex.py to regenerate. -->",
        "",
    ]

    for idx_doc in index_docs:
        idx_id = idx_doc["id"]
        idx_title = idx_doc.get("title", idx_id)
        lines.append(f"## {idx_title} (`{idx_id}`)")
        lines.append("")

        # Children = docs whose depends_on includes this index doc's id
        children = [d for d in docs.values() if idx_id in fwd.get(d["id"], [])]
        children.sort(key=lambda d: d["id"])

        if children:
            lines.append("| id | title | type | status |")
            lines.append("|----|-------|------|--------|")
            for child in children:
                c_id = child["id"]
                c_title = child.get("title", c_id)
                c_type = child.get("type", "")
                c_status = child.get("status", "")
                lines.append(f"| {c_id} | {c_title} | {c_type} | {c_status} |")
        else:
            lines.append("_(no children)_")

        lines.append("")
        lines.append("---")
        lines.append("")

    out_path = index_dir / "hierarchy.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  wrote {out_path}")


# ---------------------------------------------------------------------------
# Generate orphans.txt
# ---------------------------------------------------------------------------

def write_orphans_txt(docs: dict, fwd: dict, rev: dict, index_dir: Path) -> None:
    """Write disconnected doc ids to orphans.txt."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    orphan_ids = []
    for doc in docs.values():
        doc_id = doc["id"]
        doc_type = doc.get("type", "")
        if doc_type in ORPHAN_EXEMPT_TYPES:
            continue
        has_outbound = bool(fwd.get(doc_id))
        has_inbound = bool(rev.get(doc_id))
        if not has_outbound and not has_inbound:
            orphan_ids.append(doc_id)

    lines = [
        "# orphans — docs with no graph edges",
        f"# Generated: {now}",
        "# These docs are disconnected from the dependency graph.",
        "# Consider: add depends_on edges, or retire to status: historical.",
        "#",
        f"# Count: {len(orphan_ids)}",
        "",
    ]
    lines.extend(sorted(orphan_ids))

    out_path = index_dir / "orphans.txt"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  wrote {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) > 1:
        docs_dir = Path(sys.argv[1])
    else:
        docs_dir = DOCS_DIR

    if not docs_dir.is_dir():
        print(f"ERROR: docs directory not found: {docs_dir}", file=sys.stderr)
        return 1

    index_dir = docs_dir / ".index"
    index_dir.mkdir(exist_ok=True)

    print(f"reindex — {docs_dir}")

    docs = load_all(docs_dir)
    print(f"Loaded: {len(docs)} docs")

    fwd = forward_edges(docs)
    rev = reverse_edges(docs)

    write_dependents_json(rev, index_dir)
    write_hierarchy_md(docs, fwd, index_dir)
    write_orphans_txt(docs, fwd, rev, index_dir)

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
