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
    docs/.index/hierarchy.md       — index doc children rollup
    docs/.index/orphans.txt        — disconnected docs

Stdlib only. No external dependencies.
These files are DERIVED. Never hand-edit them; rerun this script instead.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure scripts/ is on sys.path so livedocs is importable from any CWD
sys.path.insert(0, str(Path(__file__).resolve().parent))

from livedocs import (
    DOCS_DIR, load_all, forward_edges, reverse_edges, referenced_by, doc_prefix,
)


# ---------------------------------------------------------------------------
# Types exempt from orphan detection (graph roots by design)
# ---------------------------------------------------------------------------

ORPHAN_EXEMPT_TYPES = {"index", "type"}


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
# Markers for generated children rollup in index doc bodies
# ---------------------------------------------------------------------------

_BEGIN_MARKER = "<!-- BEGIN GENERATED CHILDREN -->"
_END_MARKER = "<!-- END GENERATED CHILDREN -->"

# Legacy single-line marker written before marker-pair convention was introduced.
# Matched so we can upgrade old docs on first run.
_LEGACY_MARKER_RE = re.compile(
    r"<!-- Generated rollup — do not hand-edit\. Run `python scripts/reindex` to regenerate\. -->"
)


def _build_children_block(docs: dict, fwd: dict, idx_id: str) -> str:
    """
    Build the generated children block (everything BETWEEN the markers, inclusive
    of a header line).

    Format per child:
        ### <title> (`<id>`) — <type> / <status>
        <summary or "(no summary)">

    Returns a string that starts and ends with a newline.
    """
    children = [d for d in docs.values() if idx_id in fwd.get(d["id"], [])]
    children.sort(key=lambda d: d["id"])

    lines = [""]

    if not children:
        lines.append("_(no children)_")
        lines.append("")
        return "\n".join(lines)

    for child in children:
        c_id = child["id"]
        c_title = child.get("title", c_id)
        c_type = child.get("type", "")
        c_status = child.get("status", "")
        c_summary = child.get("summary", "").strip()

        lines.append(f"### {c_title} (`{c_id}`) — {c_type} / {c_status}")
        lines.append("")
        if c_summary:
            lines.append(c_summary)
        else:
            lines.append("_(no summary)_")
        lines.append("")

    return "\n".join(lines)


def _inject_rollup_into_body(body: str, children_block: str) -> str:
    """
    Replace or insert the generated children section in a doc body.

    Strategy:
    1. If BEGIN/END markers are present, replace the content between them.
    2. If only a legacy single-line marker is present, replace from that line
       through the next blank line + table content up to the next `##` or EOF.
       Actually: replace the legacy marker + the paragraph/table below it with
       the new marker-pair + children_block.
    3. If no marker is found, append a new `## Children` section at the end.

    Always returns the updated body string.
    """
    # Strategy 1: existing marker pair — replace content between markers
    begin_pos = body.find(_BEGIN_MARKER)
    end_pos = body.find(_END_MARKER)
    if begin_pos != -1 and end_pos != -1:
        after_end = end_pos + len(_END_MARKER)
        new_body = (
            body[:begin_pos]
            + _BEGIN_MARKER
            + children_block
            + _END_MARKER
            + body[after_end:]
        )
        return new_body

    # Strategy 2: legacy single-line marker — upgrade in place.
    # Find the legacy marker; replace from the start of its line up to either
    # the next `##` heading or end of body.
    m = _LEGACY_MARKER_RE.search(body)
    if m:
        # Scan backward to find start of the line the marker is on
        line_start = body.rfind("\n", 0, m.start())
        line_start = 0 if line_start == -1 else line_start  # keep the newline

        # Find next ## heading after the marker (start of sibling section)
        next_section = re.search(r"\n## ", body[m.end():])
        if next_section:
            section_start = m.end() + next_section.start()
        else:
            section_start = len(body)

        # Preserve the `## Children` heading that precedes the legacy marker.
        # line_start points just before the legacy marker line; preserve everything
        # up to and including the blank line after `## Children` heading.
        pre = body[:line_start]  # up to (not including) the marker's newline
        post = body[section_start:]

        new_body = (
            pre.rstrip()
            + "\n\n"
            + _BEGIN_MARKER
            + children_block
            + _END_MARKER
            + ("\n" + post.lstrip() if post.strip() else "\n")
        )
        return new_body

    # Strategy 3: no marker — append section
    stripped = body.rstrip()
    new_section = (
        "\n\n## Children\n\n"
        + _BEGIN_MARKER
        + children_block
        + _END_MARKER
        + "\n"
    )
    return stripped + new_section


def _split_frontmatter(text: str) -> tuple[str, str]:
    """
    Split a doc file into (frontmatter_block, body) where frontmatter_block
    includes the leading '---' and the trailing '---\n' delimiters verbatim.

    This lets us rewrite only the body without touching the frontmatter bytes,
    which avoids triggering any serialize round-trip bugs.

    If the file does not have a valid frontmatter block, returns ("", text).
    """
    if not text.startswith("---"):
        return "", text
    # Find the closing '---' delimiter (must be on its own line)
    end = text.find("\n---\n", 3)
    if end == -1:
        # Allow trailing-EOF form: '---\n' at end of file
        if text.rstrip().endswith("\n---"):
            end = text.rstrip().rfind("\n---")
        else:
            return "", text
    # frontmatter includes everything up to and including the closing '---\n'
    fm_block = text[:end + len("\n---\n")]
    body = text[len(fm_block):]
    return fm_block, body


def write_index_body_rollups(docs: dict, fwd: dict, docs_dir: Path) -> None:
    """
    Write a generated children rollup (with summaries) into every index doc body.

    The rollup is bracketed by BEGIN/END GENERATED CHILDREN markers so reindex
    is idempotent: re-running replaces only the generated block, leaving the
    surrounding body unchanged.

    A `## Children` section is appended if no section/marker exists yet.

    Frontmatter bytes are preserved verbatim — this function rewrites only the
    body portion of each file to avoid triggering any serialize round-trip bugs.
    """
    index_docs = [d for d in docs.values() if d.get("type") == "index"]
    index_docs.sort(key=lambda d: d["id"])

    for idx_doc in index_docs:
        idx_id = idx_doc["id"]
        path = docs_dir / f"{idx_id}.md"
        if not path.exists():
            print(f"  SKIP {idx_id} — file not found")
            continue

        file_text = path.read_text(encoding="utf-8")
        fm_block, body = _split_frontmatter(file_text)

        children_block = _build_children_block(docs, fwd, idx_id)
        new_body = _inject_rollup_into_body(body, children_block)

        if new_body == body:
            print(f"  unchanged {path.name}")
            continue

        path.write_text(fm_block + new_body, encoding="utf-8")
        print(f"  updated  {path.name}")


# ---------------------------------------------------------------------------
# Generate hierarchy.md
# ---------------------------------------------------------------------------

def write_hierarchy_md(docs: dict, fwd: dict, index_dir: Path) -> None:
    """Write index-doc hierarchy rollup to hierarchy.md.

    Children are docs that have a hard edge (requires or belongs_to) pointing
    at an index doc.
    """
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

        # Children = docs that have a hard edge pointing at this index doc
        children = [d for d in docs.values() if idx_id in fwd.get(d["id"], [])]
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

def write_orphans_txt(docs: dict, fwd: dict, rev: dict, index_dir: Path) -> None:
    """Write disconnected doc ids to orphans.txt.

    A doc is an orphan if it has no outbound hard edges (requires/belongs_to)
    and no inbound hard edges (dependents).  Navigation-only edges (relates,
    provenance, superseded_by) do NOT count for orphan purposes.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    orphans = []
    for doc in docs.values():
        doc_id = doc["id"]
        doc_type = doc.get("type", "")
        if doc_type in ORPHAN_EXEMPT_TYPES:
            continue
        has_outbound = bool(fwd.get(doc_id))
        has_inbound = bool(rev.get(doc_id))
        if not has_outbound and not has_inbound:
            orphans.append(doc)

    orphans.sort(key=lambda d: d["id"])

    lines = [
        "# orphans — docs with no hard graph edges",
        f"# Generated: {now}",
        "# These docs have no requires, belongs_to edges (outbound or inbound).",
        "# Consider: add requires/belongs_to edges, or retire to status: deprecated.",
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

    # forward_edges and reverse_edges now cover requires + belongs_to (both cascade-hard)
    fwd = forward_edges(docs)
    rev = reverse_edges(docs)
    ref_by = referenced_by(docs)  # provenance reverse map (navigation only)

    write_dependents_json(rev, index_dir)
    write_referenced_by_json(ref_by, index_dir)
    write_hierarchy_md(docs, fwd, index_dir)
    write_orphans_txt(docs, fwd, rev, index_dir)
    write_index_body_rollups(docs, fwd, docs_dir)

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
