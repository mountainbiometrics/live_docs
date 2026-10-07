#!/usr/bin/env python3
"""
migrate_level_to_facets.py — Move a store's docs from the retired `level` to the
facets (intent, force, realization), in bulk.

Usage:
    PYTHONPATH=<checkout with the facets-aware livedocs>/scripts \\
        python3 -P scripts/migrate_level_to_facets.py <docs_dir>

Run it with PYTHONPATH pointing at a checkout whose `livedocs` package carries the
facets: the script reads TYPE_TABLE and the serializer from there rather than
restating either. `-P` keeps Python from putting this script's own directory
first on the path, which would shadow that package with the checkout the script
sits in whenever that checkout still holds the old code.

For every doc in <docs_dir>:

* `level` is dropped.
* A type whose table entry requires `force` gets one: `must` when the old level was
  `requirement`, else `should` (the default when the source never said a rule).
* `intent` is `incidental` when the old level was `incidental`. Any other old level
  says nothing about what the person did, so intent is left absent for a person
  to assess. A missing intent is shown as Unattributed and weighs as incidental.
  Reference docs carry none.
* A type whose table entry requires `realization` gets `unassessed`, since nobody
  has checked the implementation. A doc at the retired `status: target` is left
  alone: what its status and realization become is a judgment, not a mapping.

Facets a doc already carries are never overwritten, so a second run changes
nothing. Docs are rewritten through the serializer, so frontmatter lands in
canonical order and the body is unchanged.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from livedocs.model import RETIRED_STATUSES, TYPE_TABLE
from livedocs.serialize import dump_doc, parse_doc

# The only level values the retired schema allowed; anything else is a doc this
# script has never been told how to read.
_OLD_LEVELS = {"incidental", "trial", "preference", "requirement"}


def migrate_doc(fm: dict) -> dict:
    """Return the doc's frontmatter with `level` replaced by the facets it implies."""
    spec = TYPE_TABLE.get(fm.get("type"))
    if spec is None:
        raise SystemExit(f"{fm['id']}: type {fm.get('type')!r} is not in TYPE_TABLE")
    level = fm.pop("level", None)
    if level is not None and level not in _OLD_LEVELS:
        raise SystemExit(f"{fm['id']}: unknown level {level!r}; refusing to guess")

    if spec.intent != "forbidden" and level == "incidental":
        fm.setdefault("intent", "incidental")
    if spec.force == "required":
        fm.setdefault("force", "must" if level == "requirement" else "should")
    if spec.realization == "required" and fm.get("status") not in RETIRED_STATUSES:
        fm.setdefault("realization", "unassessed")
    return fm


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("docs_dir", type=Path, help="directory of the store's docs")
    docs_dir = parser.parse_args(argv).docs_dir
    if not docs_dir.is_dir():
        raise SystemExit(f"not a directory: {docs_dir}")

    touched = Counter()
    by_type = Counter()
    total = 0
    for path in sorted(docs_dir.glob("*.md")):
        total += 1
        original = path.read_text(encoding="utf-8")
        fm = parse_doc(path)
        if "body" not in fm or "type" not in fm:
            raise SystemExit(f"{path.name}: no frontmatter; refusing to guess")
        body = fm.pop("body")
        migrated = migrate_doc(dict(fm, id=fm["id"]))
        text = dump_doc(migrated, body)
        if text == original:
            continue
        path.write_text(text, encoding="utf-8")
        touched["docs"] += 1
        by_type[fm["type"]] += 1
        for facet in ("intent", "force", "realization"):
            if migrated.get(facet) is not None and facet not in fm:
                touched[f"{facet}={migrated[facet]}"] += 1

    print(f"{total} docs read, {touched['docs']} rewritten")
    for key in sorted(k for k in touched if k != "docs"):
        print(f"  set {key}: {touched[key]}")
    for doc_type in sorted(by_type):
        print(f"  rewritten {doc_type}: {by_type[doc_type]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
