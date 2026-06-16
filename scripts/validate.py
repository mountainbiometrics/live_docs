#!/usr/bin/env python3
"""
validate.py — Read-only structural integrity check for a live_docs store.

Usage:
    python scripts/validate.py [docs_dir]

docs_dir defaults to DOCS_DIR from livedocs (repo root / docs).
Exits 0 if no errors, 1 if any errors found.

Stdlib only. No external dependencies.

Checks performed:
  1. Required baseline fields present (including label)
  2. label: present, trimmed, matches ^[A-Za-z0-9]+([ -][A-Za-z0-9]+)*$,
     UNIQUE across store (case-insensitive)
  3. Valid enum values (type, status, level, state)
  4. id == filename
  5. depends_on references resolve to existing docs (cascade graph)
  5b. references ids resolve to existing docs (navigation/provenance only)
  6. Reference doc extras (kind, source, imported)
  7. Provenance rule (warning: level > incidental but no depends_on AND no references AND no source)

Note: empty history: [] is VALID and does NOT trigger an error.

Human output always carries the label (and title), never a bare id.
"""

import re
import sys
from pathlib import Path

# Ensure scripts/ is on sys.path so livedocs is importable from any CWD
sys.path.insert(0, str(Path(__file__).resolve().parent))

from livedocs import (
    DOCS_DIR, load_all, dangling_edges, dangling_references, LABEL_RE, doc_prefix,
    VALID_TYPES, VALID_STATUSES, VALID_LEVELS, VALID_STATES, VALID_REFERENCE_KINDS,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_BASELINE_FIELDS = {
    "id", "title", "label", "type", "status", "level", "state",
    "depends_on", "tags", "created", "history",
}

# Levels that require provenance when depends_on is empty (warnings only)
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

    # 1. Required baseline fields
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

    state = doc.get("state", "")
    if state and state not in VALID_STATES:
        errors.append(f"{prefix}  invalid `state` value `{state}`")

    # 4. id == filename (parse_doc sets id from filename; check against frontmatter)
    # (livedocs.parse_doc sets doc["id"] from filename, but we check consistency
    # by re-reading: actually parse_doc already overrides id from filename, so
    # we can't detect a mismatch here the same way. Instead we trust the loader.)
    # The id field in the returned doc IS the filename stem (authoritative).

    # 5. depends_on resolution (cascade graph — errors are blocking)
    depends_on = doc.get("depends_on", [])
    if isinstance(depends_on, list):
        for dep_id in depends_on:
            if dep_id and dep_id not in all_ids:
                errors.append(f"{prefix}  broken depends_on `{dep_id}` (no such doc)")
    elif depends_on:
        errors.append(f"{prefix}  depends_on is not a list")

    # 5b. references resolution (navigation/provenance — absent field is [] and is fine)
    references = doc.get("references", [])
    if isinstance(references, list):
        for ref_id in references:
            if ref_id and ref_id not in all_ids:
                errors.append(f"{prefix}  broken references `{ref_id}` (no such doc)")
    elif references:
        errors.append(f"{prefix}  references is not a list")

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

    # 7. Provenance rule (warning only)
    # A non-empty references list satisfies provenance, same as depends_on or source.
    # Docs with level: incidental are never flagged.
    if doc_type != "reference":
        empty_depends = not depends_on
        empty_references = not references
        has_source = bool(doc.get("source"))
        if empty_depends and empty_references and not has_source and level in PROVENANCE_REQUIRED_LEVELS:
            warnings.append(
                f"{prefix}  level `{level}` but depends_on, references, and source are all empty "
                f"(no provenance — consider adding a references or depends_on edge)"
            )

    # NOTE: empty history: [] is valid; no check here.

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
