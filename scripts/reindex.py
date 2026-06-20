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
    docs/.index/orphans.txt        — docs with no belongs_to lineage (hierarchy-based)

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
    DOCS_DIR, load_all, reverse_edges, referenced_by, doc_prefix,
)


# ---------------------------------------------------------------------------
# Orphan exemption (per 20260619235049 — hierarchy-based, belongs_to lineage)
# ---------------------------------------------------------------------------
#
# With `type:index` retired, orphan-hood is now defined off the belongs_to
# hierarchy, not off a type marker. A doc with no belongs_to lineage is an
# orphan ONLY IF it is not a legitimate top-level node:
#
#   - `component` docs are legitimate structural roots — the root component and
#     the structural subsystems each anchor a scope and intentionally sit at the
#     top of the tree with no belongs_to parent. They are NOT orphans.
#
#   - `reference` docs (raw clippings, brainstorms, plans, external material) are
#     supporting evidence wired into the graph via `provenance`, not `belongs_to`.
#     They are legitimately edge-light in the hierarchy, so flagging them as
#     orphans is pure noise. They are NOT orphans.
#
# Any OTHER type with no belongs_to lineage (in or out) fell out of the hierarchy
# by accident and IS an orphan.
ORPHAN_EXEMPT_TYPES = {"component", "reference"}


# ---------------------------------------------------------------------------
# belongs_to-only edge maps (hierarchy / lineage — NOT requires)
# ---------------------------------------------------------------------------

def belongs_to_forward(docs: dict) -> dict:
    """Map {id: [belongs_to targets that exist in docs]} — lineage edges only."""
    all_ids = set(docs.keys())
    return {
        doc_id: [t for t in doc.get("belongs_to", []) if t in all_ids]
        for doc_id, doc in docs.items()
    }


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
# Generate orphans.txt
# ---------------------------------------------------------------------------

def write_orphans_txt(docs: dict, bt_fwd: dict, bt_rev: dict, index_dir: Path) -> None:
    """Write hierarchy-disconnected doc ids to orphans.txt.

    Per 20260619235049, orphan-hood is now defined off the `belongs_to`
    hierarchy (lineage), NOT off a type marker:

      A doc with NO belongs_to lineage — no belongs_to parent (outbound) and no
      descendants (inbound) — is an orphan UNLESS it is a legitimate top-level
      node. `component` docs (intentional structural roots that anchor scopes)
      and `reference` docs (supporting evidence wired in via provenance, not
      belongs_to) are exempt; see ORPHAN_EXEMPT_TYPES.

    requires / relates / provenance / superseded_by do NOT count for orphan
    purposes — only belongs_to lineage does.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    orphans = []
    for doc in docs.values():
        doc_id = doc["id"]
        doc_type = doc.get("type", "")
        if doc_type in ORPHAN_EXEMPT_TYPES:
            continue
        has_parent = bool(bt_fwd.get(doc_id))      # outbound belongs_to
        has_descendants = bool(bt_rev.get(doc_id))  # inbound belongs_to
        if not has_parent and not has_descendants:
            orphans.append(doc)

    orphans.sort(key=lambda d: d["id"])

    lines = [
        "# orphans — docs with no belongs_to lineage",
        f"# Generated: {now}",
        "# These docs have no belongs_to parent and no descendants, and are not a",
        "# legitimate top-level node (component / reference are exempt).",
        "# Consider: add a belongs_to edge into the hierarchy, or retire to deprecated.",
        "# Format: <id> [<label>] \"<Type>: <Title>\"",
        "#",
        f"# Count: {len(orphans)}",
        "",
    ]
    for doc in orphans:
        lines.append(doc_prefix(doc))

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

    # dependents.json is the CASCADE INPUT — requires + belongs_to (both hard).
    rev = reverse_edges(docs)
    ref_by = referenced_by(docs)  # provenance reverse map (navigation only)

    # hierarchy / orphans are LINEAGE artifacts — belongs_to only, never requires.
    bt_fwd = belongs_to_forward(docs)
    bt_rev = belongs_to_reverse(docs)

    write_dependents_json(rev, index_dir)
    write_referenced_by_json(ref_by, index_dir)
    write_hierarchy_md(docs, bt_rev, index_dir)
    write_orphans_txt(docs, bt_fwd, bt_rev, index_dir)

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
