#!/usr/bin/env python3
"""
edges.py — Print forward/reverse edge maps and dangling-edge report.

Usage:
    python scripts/edges.py [--json]

Without --json: prints a human-readable summary.
With --json: prints a machine-readable JSON object with keys:
    forward    — {id: [dep_ids]}
    reverse    — {id: [dependent_ids]}
    titles     — {id: title}
    dangling   — [[from_id, missing_dep_id], ...]

This is the canonical tool for building edge maps; cascade-check and other
verification scripts should call this rather than re-implementing the logic.

Stdlib only. No external dependencies.
"""

import json
import sys
from pathlib import Path

# Ensure scripts/ is on sys.path so livedocs is importable from any CWD
sys.path.insert(0, str(Path(__file__).resolve().parent))

from livedocs import DOCS_DIR, load_all, forward_edges, reverse_edges, dangling_edges, id_title_map


def main() -> int:
    use_json = "--json" in sys.argv

    docs = load_all(DOCS_DIR)
    fwd = forward_edges(docs)
    rev = reverse_edges(docs)
    titles = id_title_map(docs)
    dangling = dangling_edges(docs)

    if use_json:
        output = {
            "forward": {k: sorted(v) for k, v in sorted(fwd.items())},
            "reverse": {k: sorted(v) for k, v in sorted(rev.items())},
            "titles": {k: v for k, v in sorted(titles.items())},
            "dangling": [[a, b] for a, b in sorted(dangling)],
        }
        print(json.dumps(output, indent=2))
        return 1 if dangling else 0

    # Human-readable output
    print(f"edges — {DOCS_DIR}")
    print(f"Docs: {len(docs)}")
    print()

    print("FORWARD EDGES (id → depends_on)")
    for doc_id in sorted(fwd):
        deps = fwd[doc_id]
        dep_str = ", ".join(deps) if deps else "(none)"
        print(f"  {doc_id}  →  {dep_str}")
    print()

    print("REVERSE EDGES (id → dependents)")
    for doc_id in sorted(rev):
        dependents = rev[doc_id]
        dep_str = ", ".join(sorted(dependents)) if dependents else "(none)"
        print(f"  {doc_id}  ←  {dep_str}")
    print()

    if dangling:
        print("DANGLING EDGES (depends_on targets that do not exist):")
        for from_id, missing_id in sorted(dangling):
            from_title = titles.get(from_id, from_id)
            print(f"  [DANGLING] {from_id} ({from_title!r}) → {missing_id} (missing)")
        print()
        print(f"Summary: {len(docs)} docs, {len(dangling)} dangling edge(s)")
        return 1
    else:
        print(f"Summary: {len(docs)} docs, 0 dangling edges — graph is clean.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
