#!/usr/bin/env python3
"""
reindex.py — Rebuild generated artifacts in docs/.index/.

Usage:
    python scripts/reindex.py [docs_dir]

docs_dir defaults to DOCS_DIR from livedocs (repo root / docs).

Generates:
    docs/.index/dependents.json    — reverse-dependency map (requires + belongs_to;
                                     CASCADE INPUT)
    docs/.index/referenced_by.json — reverse-provenance map (provenance field only;
                                     NAVIGATION ONLY, NOT cascade)
    docs/.index/hierarchy.md       — children rollup under every descendant-bearing
                                     doc (any doc targeted by belongs_to)

Orphan detection is NOT a derived artifact here. Orphan-hood is pure belongs_to
topology that consumers must query FRESH, not read from a stale cache. The single
source of truth is `kb.orphans()` / `ldoc orphans`.

Stdlib only. No external dependencies.
These files are DERIVED. Never hand-edit them; rerun this script instead.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure scripts/ is on sys.path so livedocs is importable from any CWD
sys.path.insert(0, str(Path(__file__).resolve().parent))

from livedocs import (
    DOCS_DIR, load_all, reverse_edges, referenced_by,
)


# ---------------------------------------------------------------------------
# belongs_to-only edge maps (hierarchy / lineage — NOT requires)
# ---------------------------------------------------------------------------

def belongs_to_reverse(docs: dict) -> dict:
    """Map {id: [ids that belongs_to this doc]} — i.e. each doc's descendants' parents."""
    all_ids = set(docs.keys())
    rev: dict = {doc_id: [] for doc_id in all_ids}
    for doc_id, doc in docs.items():
        for target in doc.get("belongs_to", []):
            if target in rev:
                rev[target].append(doc_id)
    return rev


# ---------------------------------------------------------------------------
# Generate dependents.json (CASCADE INPUT — requires + belongs_to edges)
# ---------------------------------------------------------------------------

def write_dependents_json(rev: dict, index_dir: Path) -> None:
    """
    Write reverse-dependency map to dependents.json.

    This is the CASCADE INPUT — derived from requires + belongs_to edges (both
    are cascade-hard).  Never includes provenance, relates, or superseded_by.
    """
    output = {k: sorted(v) for k, v in sorted(rev.items())}
    out_path = index_dir / "dependents.json"
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"  wrote {out_path}")


# ---------------------------------------------------------------------------
# Generate referenced_by.json (NAVIGATION ONLY — provenance edges, NOT cascade)
# ---------------------------------------------------------------------------

def write_referenced_by_json(ref_by: dict, index_dir: Path) -> None:
    """
    Write reverse-provenance map to referenced_by.json.

    NAVIGATION ARTIFACT ONLY — derived from the `provenance` frontmatter field.
    This is immutable derivation lineage ("was derived from" / "informed by").
    MUST NOT be used as cascade input. Use dependents.json for cascade.
    """
    output = {k: sorted(v) for k, v in sorted(ref_by.items())}
    out_path = index_dir / "referenced_by.json"
    out_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"  wrote {out_path}")


# ---------------------------------------------------------------------------
# Generate hierarchy.md
# ---------------------------------------------------------------------------

def write_hierarchy_md(docs: dict, bt_rev: dict, index_dir: Path) -> None:
    """Write the hierarchy rollup to hierarchy.md.

    With `type:index` retired, the navigational-signpost role is STRUCTURAL: any
    doc that has descendants — i.e. is targeted by one or more `belongs_to` edges
    — plays the signpost role. We therefore roll up children under EVERY
    descendant-bearing doc (any doc with a non-empty belongs_to reverse list),
    regardless of its type. Children are the docs that `belongs_to` it.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Parents = docs that have at least one descendant via belongs_to.
    parent_docs = [d for d in docs.values() if bt_rev.get(d["id"])]
    parent_docs.sort(key=lambda d: d["id"])

    lines = [
        "# live_docs Hierarchy",
        f"<!-- Generated: {now} — do not hand-edit. Run reindex.py to regenerate. -->",
        "",
        "<!-- Rollup of every descendant-bearing doc (any doc targeted by belongs_to). -->",
        "",
    ]

    for parent in parent_docs:
        p_id = parent["id"]
        p_type = parent.get("type", "")
        p_title = parent.get("title", p_id)
        lines.append(f"## {p_title} (`{p_id}`, {p_type})")
        lines.append("")

        # Children = docs that belongs_to this parent.
        children = [docs[cid] for cid in bt_rev.get(p_id, []) if cid in docs]
        children.sort(key=lambda d: d["id"])

        if children:
            lines.append("| id | label | title | type | status |")
            lines.append("|----|-------|-------|------|--------|")
            for child in children:
                c_id = child["id"]
                c_label = child.get("label", "")
                c_title = child.get("title", c_id)
                c_type = child.get("type", "")
                c_status = child.get("status", "")
                lines.append(f"| {c_id} | {c_label} | {c_title} | {c_type} | {c_status} |")
        else:
            lines.append("_(no children)_")

        lines.append("")
        lines.append("---")
        lines.append("")

    out_path = index_dir / "hierarchy.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
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

    # dependents.json is the CASCADE INPUT — requires + belongs_to (both hard).
    rev = reverse_edges(docs)
    ref_by = referenced_by(docs)  # provenance reverse map (navigation only)

    # hierarchy is a LINEAGE artifact — belongs_to reverse map only, never requires.
    bt_rev = belongs_to_reverse(docs)

    write_dependents_json(rev, index_dir)
    write_referenced_by_json(ref_by, index_dir)
    write_hierarchy_md(docs, bt_rev, index_dir)

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
