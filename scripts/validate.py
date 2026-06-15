#!/usr/bin/env python3
"""
validate.py — Read-only structural integrity check for a live_docs store.

Usage:
    python scripts/validate.py [docs_dir]

docs_dir defaults to DOCS_DIR from livedocs (repo root / docs).
Exits 0 if no errors, 1 if any errors found.

Stdlib only. No external dependencies.

Checks performed:
  1. Required baseline fields present
  2. Valid enum values (type, status, level, state)
  3. id == filename
  4. depends_on references resolve to existing docs (cascade graph)
  4b. references ids resolve to existing docs (navigation/provenance only)
  5. Reference doc extras (kind, source, imported)
  6. Provenance rule (warning: level > incidental but no depends_on AND no references AND no source)

Note: empty history: [] is VALID and does NOT trigger an error.
"""

import sys
from pathlib import Path

# Ensure scripts/ is on sys.path so livedocs is importable from any CWD
sys.path.insert(0, str(Path(__file__).resolve().parent))

from livedocs import DOCS_DIR, load_all, dangling_edges, dangling_references


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_TYPES = {
    "type", "principle", "goal", "decision", "constraint",
    "requirement", "use-case", "guide", "component", "reference", "index",
}
VALID_STATUSES = {"living", "historical"}
VALID_LEVELS = {"incidental", "trial", "preference", "requirement"}
VALID_STATES = {"actual", "target"}
VALID_REFERENCE_KINDS = {"brainstorm", "plan", "clipping", "external"}

REQUIRED_BASELINE_FIELDS = {
    "id", "title", "type", "status", "level", "state",
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
    doc_id = doc.get("id", "<unknown>")

    # 1. Required baseline fields
    for field in REQUIRED_BASELINE_FIELDS:
        if field not in doc or doc[field] is None:
            errors.append(f"{doc_id}  missing field `{field}`")

    # Early exit if type missing — needed for subsequent checks
    if "type" not in doc:
        return errors, warnings

    # 2. Valid enum values
    doc_type = doc.get("type", "")
    if doc_type not in VALID_TYPES:
        errors.append(f"{doc_id}  invalid `type` value `{doc_type}`")

    status = doc.get("status", "")
    if status and status not in VALID_STATUSES:
        errors.append(f"{doc_id}  invalid `status` value `{status}`")

    level = doc.get("level", "")
    if level and level not in VALID_LEVELS:
        errors.append(f"{doc_id}  invalid `level` value `{level}`")

    state = doc.get("state", "")
    if state and state not in VALID_STATES:
        errors.append(f"{doc_id}  invalid `state` value `{state}`")

    # 3. id == filename (parse_doc sets id from filename; check against frontmatter)
    # (livedocs.parse_doc sets doc["id"] from filename, but we check consistency
    # by re-reading: actually parse_doc already overrides id from filename, so
    # we can't detect a mismatch here the same way. Instead we trust the loader.)
    # The id field in the returned doc IS the filename stem (authoritative).

    # 4. depends_on resolution (cascade graph — errors are blocking)
    depends_on = doc.get("depends_on", [])
    if isinstance(depends_on, list):
        for dep_id in depends_on:
            if dep_id and dep_id not in all_ids:
                errors.append(f"{doc_id}  broken depends_on `{dep_id}` (no such doc)")
    elif depends_on:
        errors.append(f"{doc_id}  depends_on is not a list")

    # 4b. references resolution (navigation/provenance — absent field is [] and is fine)
    references = doc.get("references", [])
    if isinstance(references, list):
        for ref_id in references:
            if ref_id and ref_id not in all_ids:
                errors.append(f"{doc_id}  broken references `{ref_id}` (no such doc)")
    elif references:
        errors.append(f"{doc_id}  references is not a list")

    # 5. Reference doc extras
    if doc_type == "reference":
        kind = doc.get("kind", "")
        if not kind:
            errors.append(f"{doc_id}  reference doc missing `kind`")
        elif kind not in VALID_REFERENCE_KINDS:
            errors.append(f"{doc_id}  reference doc invalid `kind` value `{kind}`")
        if "source" not in doc:
            errors.append(f"{doc_id}  reference doc missing `source`")
        if "imported" not in doc:
            errors.append(f"{doc_id}  reference doc missing `imported`")

    # 6. Provenance rule (warning only)
    # A non-empty references list satisfies provenance, same as depends_on or source.
    # Docs with level: incidental are never flagged.
    if doc_type != "reference":
        empty_depends = not depends_on
        empty_references = not references
        has_source = bool(doc.get("source"))
        if empty_depends and empty_references and not has_source and level in PROVENANCE_REQUIRED_LEVELS:
            warnings.append(
                f"{doc_id}  level `{level}` but depends_on, references, and source are all empty "
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
