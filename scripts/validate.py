#!/usr/bin/env python3
"""
validate.py — Read-only structural integrity check for a live_docs store.

Usage:
    python scripts/validate.py [docs_dir]

docs_dir defaults to DOCS_DIR from livedocs (repo root / docs).
Exits 0 if no errors, 1 if any errors found.

Stdlib only. No external dependencies.

Checks performed:
  1. Required baseline fields present (id, title, label, type, status, level, created)
  2. label: present, trimmed, UNIQUE across store (case-insensitive)
  3. Valid enum values (type, status, level)
  4. id == filename
  5a. requires ids resolve to existing docs (cascade graph — errors blocking)
  5b. belongs_to ids resolve to existing docs (cascade graph — errors blocking)
  5c. provenance ids that exist in docs/ resolve correctly (navigation; dangling
      to raw/ or external is a warning, not an error)
  5d. relates ids resolve to existing docs (navigation — errors blocking for in-graph refs)
  5e. superseded_by ids resolve to existing docs (blocking)
  6. Reference doc extras (kind, source, imported)
  7. deprecated docs MUST have a non-empty superseded_by (error if missing)
  8. domain is a list; scope is a single string (topological zone)
  9. Per-edge-type acyclicity: belongs_to (a DAG) must have NO cycles (blocking)
 10. summary presence + length guideline for non-reference docs (warnings)
 11. reference doc with superseded_by but not deprecated (staged-incomplete retirement)
 12. body [[id]] wikilinks not present in any edge field (prose-not-edged)
 13. malformed body wikilinks ([[id|label]], [[id]] (label)) — canonical form is bare [[id]]

Note: empty edge fields and empty history are VALID (absent == empty).
Human output always carries the label (and title), never a bare id.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Ensure scripts/ is on sys.path so livedocs is importable from any CWD
sys.path.insert(0, str(Path(__file__).resolve().parent))

from livedocs import (
    DOCS_DIR, load_all, dangling_edges, dangling_references, doc_prefix,
    VALID_TYPES, VALID_STATUSES, VALID_LEVELS, VALID_REFERENCE_KINDS,
)
from livedocs.lint import prose_links_not_edged, malformed_body_wikilinks


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Fields that must always be present (scalar or tag-map fields).
# Edge fields (belongs_to, requires, relates, provenance, superseded_by) are
# optional and may be absent — absence == empty list, which is valid.
REQUIRED_BASELINE_FIELDS = {
    "id", "title", "label", "type", "status", "level", "created",
}

# Edge fields the model treats as DAGs (no cycles permitted). belongs_to is the
# family-tree edge whose genealogy effective-scope walks, so a cycle there would
# make that walk non-terminating — hence a hard error.
DAG_EDGE_FIELDS = ("belongs_to",)


# ---------------------------------------------------------------------------
# Per-doc check
# ---------------------------------------------------------------------------

def check_doc(doc: dict, all_ids: set, *, children_of: dict[str, set[str]] | None = None) -> tuple[list, list]:
    """
    Return (errors, warnings) for one parsed doc dict.
    Each item is a string describing the violation.
    """
    errors = []
    warnings = []
    prefix = doc_prefix(doc)

    # 1. Required baseline fields (absent or None is an error)
    for field in REQUIRED_BASELINE_FIELDS:
        if field not in doc or doc[field] is None:
            errors.append(f"{prefix}  missing field `{field}`")

    # Early exit if type missing — needed for subsequent checks
    if "type" not in doc:
        return errors, warnings

    # 2. Label validation: present and trimmed (uniqueness checked in main).
    # No character-format restriction — labels are free-form human identifiers.
    label = doc.get("label", "")
    if not label:
        errors.append(f"{prefix}  missing or empty `label`")
    elif label != label.strip():
        errors.append(f"{prefix}  `label` value {label!r} has leading/trailing whitespace")

    # 3. Valid enum values
    doc_type = doc.get("type", "")
    if doc_type not in VALID_TYPES:
        errors.append(f"{prefix}  invalid `type` value `{doc_type}`")

    status = doc.get("status", "")
    if status and status not in VALID_STATUSES:
        errors.append(f"{prefix}  invalid `status` value `{status}`")

    level = doc.get("level", "")
    if level and level not in VALID_LEVELS:
        errors.append(f"{prefix}  invalid `level` value `{level}`")

    # Tags: `domain` and `keywords` are flat top-level lists; `scope` is a single
    # STRING naming a topological zone (per the scope-as-topology reframe).
    for tag_key in ("domain", "keywords"):
        tag_val = doc.get(tag_key)
        if tag_val is not None and not isinstance(tag_val, list):
            errors.append(f"{prefix}  `{tag_key}` is not a list")
        elif isinstance(tag_val, list):
            for item in tag_val:
                if not isinstance(item, str):
                    errors.append(f"{prefix}  `{tag_key}` contains non-string entry")
                elif item != item.strip():
                    warnings.append(f"{prefix}  `{tag_key}` entry {item!r} has leading/trailing whitespace")
            lowered = [i.lower() for i in tag_val if isinstance(i, str)]
            if len(lowered) != len(set(lowered)):
                warnings.append(f"{prefix}  `{tag_key}` contains duplicate entries (case-insensitive)")
    scope_val = doc.get("scope")
    if scope_val is not None and not isinstance(scope_val, str):
        errors.append(f"{prefix}  `scope` is not a string (it now names a single topological zone)")

    # 5a-5b, 5d-5e. Hard/navigation edge resolution (errors are blocking)
    for edge_field in ("requires", "belongs_to", "relates", "superseded_by"):
        val = doc.get(edge_field, [])
        if isinstance(val, list):
            for target_id in val:
                if target_id and target_id not in all_ids:
                    errors.append(f"{prefix}  broken {edge_field} `{target_id}` (no such doc)")
        elif val:
            errors.append(f"{prefix}  {edge_field} is not a list")

    # 5c. provenance resolution (navigation only; dangling to raw/ is a warning)
    provenance = doc.get("provenance", [])
    if isinstance(provenance, list):
        for prov_id in provenance:
            if prov_id and prov_id not in all_ids:
                warnings.append(
                    f"{prefix}  provenance `{prov_id}` not found in docs/ "
                    f"(may be raw/ or external — ok if intentional)"
                )
    elif provenance:
        errors.append(f"{prefix}  provenance is not a list")

    # Collect edge lists used in later checks
    superseded_by = doc.get("superseded_by", [])

    # 6. Reference doc extras
    if doc_type == "reference":
        kind = doc.get("kind", "")
        if not kind:
            errors.append(f"{prefix}  reference doc missing `kind`")
        elif kind not in VALID_REFERENCE_KINDS:
            errors.append(f"{prefix}  reference doc invalid `kind` value `{kind}`")
        if "source" not in doc:
            errors.append(f"{prefix}  reference doc missing `source`")
        if "imported" not in doc:
            errors.append(f"{prefix}  reference doc missing `imported`")

    # 7. deprecated docs MUST have superseded_by
    if status == "deprecated":
        if not superseded_by:
            errors.append(
                f"{prefix}  status `deprecated` but `superseded_by` is empty — "
                f"add a superseded_by edge pointing to the replacement doc(s)"
            )

    # 11. staged-incomplete retirement: superseded_by set but status is not deprecated
    if superseded_by and status != "deprecated":
        warnings.append(
            f"{prefix}  has `superseded_by` but status is `{status}` — "
            f"staged retirement incomplete (add `status: deprecated` or remove the edge)"
        )

    # Summary: non-reference docs should carry a tight summary — 1–3 sentences,
    # ~50 words, mirroring the doc's opening. WARN on missing or over-long.
    summary_text = (doc.get("summary") or "").strip()
    if doc_type != "reference":
        if not summary_text:
            warnings.append(
                f"{prefix}  no `summary` (1–3 sentence overview expected)"
            )
        else:
            wc = len(summary_text.split())
            if wc > 60:
                warnings.append(
                    f"{prefix}  `summary` is {wc} words — aim for ≤ ~50 "
                    f"(1–3 tight sentences, not a run-on)"
                )

    # 12. body wikilinks not mirrored in edge fields (report only)
    body = doc.get("body", "") or ""
    unedged = prose_links_not_edged(doc)
    if children_of:
        unedged -= children_of.get(doc["id"], set())
    for linked_id in sorted(unedged):
        warnings.append(
            f"{prefix}  body links `[[{linked_id}]]` not in any edge field "
            f"(requires/belongs_to/relates/provenance/superseded_by)"
        )

    # 13. malformed body wikilink syntax
    for kind, token in malformed_body_wikilinks(body):
        if kind == "pipe":
            warnings.append(
                f"{prefix}  body malformed wikilink {token!r} — use bare `[[<id>]]`; "
                f"labels resolve at display time"
            )
        else:
            warnings.append(
                f"{prefix}  body malformed wikilink {token!r} — use bare `[[<id>]]` only; "
                f"do not append a parenthetical label"
            )

    # NOTE: empty edge lists and empty history are valid; no check here.
    #
    # The former "provenance rule" warning (level ∈ {trial,preference,requirement}
    # with no requires/belongs_to/provenance/source) was intentionally REMOVED:
    # the model's rule is "no grounding ⇒ classify as incidental", which is
    # authoring guidance, not a validation concern.

    return errors, warnings


# ---------------------------------------------------------------------------
# Per-edge-type acyclicity (store-wide)
# ---------------------------------------------------------------------------

def find_cycles(docs: dict, edge_field: str) -> list[list[str]]:
    """
    Return a list of cycles found in the directed graph formed by `edge_field`.

    Each cycle is a list of doc ids in traversal order (the repeated node closes
    it). Only edges whose target exists in docs are followed (dangling edges are
    a separate check). Uses iterative DFS with a recursion-stack to detect a
    back-edge; reports each distinct cycle once.
    """
    all_ids = set(docs.keys())
    adj = {
        doc_id: [t for t in docs[doc_id].get(edge_field, []) if t in all_ids]
        for doc_id in docs
    }

    WHITE, GREY, BLACK = 0, 1, 2
    color = {doc_id: WHITE for doc_id in docs}
    cycles: list[list[str]] = []
    seen_cycle_keys: set[frozenset] = set()

    for root in sorted(docs):
        if color[root] != WHITE:
            continue
        # Iterative DFS carrying the active path for cycle reconstruction.
        # Each stack frame: (node, iterator over its neighbors).
        stack: list[tuple[str, list[str]]] = [(root, list(adj[root]))]
        path = [root]
        on_path = {root}
        color[root] = GREY
        while stack:
            node, neighbors = stack[-1]
            if neighbors:
                nxt = neighbors.pop()
                if color.get(nxt) == GREY and nxt in on_path:
                    # Back-edge → cycle from nxt forward through the path.
                    i = path.index(nxt)
                    cycle = path[i:] + [nxt]
                    key = frozenset(cycle)
                    if key not in seen_cycle_keys:
                        seen_cycle_keys.add(key)
                        cycles.append(cycle)
                elif color.get(nxt) == WHITE:
                    color[nxt] = GREY
                    on_path.add(nxt)
                    path.append(nxt)
                    stack.append((nxt, list(adj[nxt])))
            else:
                color[node] = BLACK
                on_path.discard(node)
                if path and path[-1] == node:
                    path.pop()
                stack.pop()

    return cycles


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

    docs = load_all(docs_dir)
    all_ids = set(docs.keys())
    doc_files_sorted = sorted(docs.values(), key=lambda d: d["id"])

    print(f"validate — {docs_dir}")
    print(f"Scanned: {len(docs)} docs")
    print()

    # Build reverse belongs_to map: parent_id → set of child ids.
    # Parents naturally reference children in prose without needing an explicit
    # forward edge — the hierarchy is already expressed on the child's side.
    children_of: dict[str, set[str]] = {}
    for doc in doc_files_sorted:
        for parent_id in doc.get("belongs_to", []) or []:
            if parent_id:
                children_of.setdefault(parent_id, set()).add(doc["id"])

    all_errors = []
    all_warnings = []

    for doc in doc_files_sorted:
        errs, warns = check_doc(doc, all_ids, children_of=children_of)
        all_errors.extend(errs)
        all_warnings.extend(warns)

    # Label uniqueness check, case-insensitive (cross-doc — after all docs loaded)
    label_to_docs: dict[str, list] = {}
    for doc in doc_files_sorted:
        label = doc.get("label", "")
        if label:
            label_to_docs.setdefault(label.lower(), []).append(doc)
    for label_lower, docs_with_label in sorted(label_to_docs.items()):
        if len(docs_with_label) > 1:
            used_by = ", ".join(doc_prefix(d) for d in docs_with_label)
            all_errors.append(
                f"label `{label_lower}` is not unique (case-insensitive) — used by: {used_by}"
            )

    # Per-edge-type acyclicity (store-wide). Each DAG edge must have NO cycles —
    # a cycle is a hard error. belongs_to in particular is load-bearing: the
    # effective-scope walk follows its genealogy, so a cycle would never
    # terminate.
    for edge_field in DAG_EDGE_FIELDS:
        for cycle in find_cycles(docs, edge_field):
            chain = " → ".join(cycle)
            all_errors.append(
                f"`{edge_field}` cycle (must be acyclic): {chain}"
            )

    if not all_errors and not all_warnings:
        print("All checks passed.")
        return 0

    if all_errors:
        print("ERRORS (must fix):")
        for e in all_errors:
            print(f"  [E] {e}")
        print()

    if all_warnings:
        print("WARNINGS (should review):")
        for w in all_warnings:
            print(f"  [W] {w}")
        print()

    print(f"Summary: {len(all_errors)} errors, {len(all_warnings)} warnings")
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
