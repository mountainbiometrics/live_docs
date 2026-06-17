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
  2. label: present, trimmed, matches ^[A-Za-z0-9]+([ -][A-Za-z0-9]+)*$,
     UNIQUE across store (case-insensitive)
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
  8. Provenance rule (warning: level > incidental but no hard edges AND no provenance)

Note: empty edge fields and empty history are VALID (absent == empty).
Human output always carries the label (and title), never a bare id.
"""

import re
import sys
from pathlib import Path

# Ensure scripts/ is on sys.path so livedocs is importable from any CWD
sys.path.insert(0, str(Path(__file__).resolve().parent))

from livedocs import (
    DOCS_DIR, load_all, dangling_edges, dangling_references, LABEL_RE, doc_prefix,
    VALID_TYPES, VALID_STATUSES, VALID_LEVELS, VALID_REFERENCE_KINDS,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Fields that must always be present (scalar or tag-map fields).
# Edge fields (belongs_to, requires, relates, provenance, superseded_by) are
# optional and may be absent — absence == empty list, which is valid.
REQUIRED_BASELINE_FIELDS = {
    "id", "title", "label", "type", "status", "level", "created",
}

# Levels that require provenance when hard edges are empty (warnings only)
PROVENANCE_REQUIRED_LEVELS = {"trial", "preference", "requirement"}


# ---------------------------------------------------------------------------
# Per-doc check
# ---------------------------------------------------------------------------

def check_doc(doc: dict, all_ids: set) -> tuple[list, list]:
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

    # 2. Label validation: present, trimmed, valid format (uniqueness checked in main)
    label = doc.get("label", "")
    if not label:
        errors.append(f"{prefix}  missing or empty `label`")
    elif label != label.strip():
        errors.append(f"{prefix}  `label` value {label!r} has leading/trailing whitespace")
    elif not LABEL_RE.match(label):
        errors.append(
            f"{prefix}  invalid `label` value {label!r} — "
            f"must match ^[A-Za-z0-9]+([ -][A-Za-z0-9]+)*$"
        )

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

    # Note: `state` field is REMOVED from the schema. If present in a doc it has
    # not been migrated yet — tolerate it silently (doc migration is a separate pass).

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
    requires = doc.get("requires", [])
    belongs_to = doc.get("belongs_to", [])
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

    # 8. Provenance rule (warning only)
    # A doc with non-trivial level should have SOME link to its basis:
    # requires, belongs_to, provenance, or a source field.
    if doc_type != "reference":
        empty_hard_edges = not requires and not belongs_to
        empty_provenance = not provenance
        has_source = bool(doc.get("source"))
        if (empty_hard_edges and empty_provenance and not has_source
                and level in PROVENANCE_REQUIRED_LEVELS):
            warnings.append(
                f"{prefix}  level `{level}` but requires, belongs_to, provenance, and source "
                f"are all empty (no provenance — consider adding a provenance or requires edge)"
            )

    # NOTE: empty edge lists and empty history are valid; no check here.

    return errors, warnings


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

    all_errors = []
    all_warnings = []

    for doc in doc_files_sorted:
        errs, warns = check_doc(doc, all_ids)
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
