"""
livedocs.py — Shared library for the live_docs tooling.

Stdlib only (pathlib, re, datetime). No external dependencies. Import from other scripts:

    from livedocs import DOCS_DIR, RAW_DIR, parse_doc, load_all, forward_edges, reverse_edges, id_title_map, generate_id

Repo-root detection: the repo root is the parent of the directory that
contains this file (scripts/ → repo root). This works regardless of CWD.
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Paths — resolved at import time, relative to THIS file's location
# ---------------------------------------------------------------------------

# scripts/livedocs.py → scripts/ → repo_root
_SCRIPTS_DIR: Path = Path(__file__).resolve().parent
REPO_ROOT: Path = _SCRIPTS_DIR.parent
DOCS_DIR: Path = REPO_ROOT / "docs"
RAW_DIR: Path = REPO_ROOT / "raw"


# ---------------------------------------------------------------------------
# Collision-safe ID generation (shared by new_doc.py and ingest_raw.py)
# ---------------------------------------------------------------------------

def generate_id(target_dir: Path) -> str:
    """
    Return a YYYYMMDDHHMMSS timestamp string that does not collide with an
    existing <id>.md file in target_dir.  If the current-second candidate is
    taken, increments by 1 second until a free slot is found.

    target_dir does not have to exist yet — the collision check simply skips
    files that cannot be found.
    """
    base = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    ts = int(base)
    while (target_dir / f"{ts}.md").exists():
        ts += 1
    return str(ts)


# ---------------------------------------------------------------------------
# Frontmatter parsing helpers (hand-rolled; handles only live_docs shapes)
# ---------------------------------------------------------------------------

def _strip_quotes(s: str) -> str:
    """Remove surrounding single or double quotes from a scalar string."""
    s = s.strip()
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        return s[1:-1]
    return s


def _parse_inline_list(s: str) -> list:
    """Parse an inline YAML list like [a, b, c] or [] into a Python list."""
    s = s.strip()
    if s == "[]":
        return []
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1]
        return [_strip_quotes(item) for item in inner.split(",") if item.strip()]
    return []


def _parse_frontmatter_text(fm_text: str) -> dict:
    """
    Parse the text between the two '---' delimiters.

    Handles the subset of YAML shapes used by live_docs:
    - Quoted scalars:    key: "value"
    - Unquoted scalars: key: value
    - Inline lists:     key: [a, b]
    - Empty lists:      key: []
    - Block sequences:  key:\n  - item     (simple strings)
    - History blocks:   history:\n  - at: "..."\n    summary: "..."
    - Nested mappings:  tags:\n  domain: []\n  scope: [live_docs]
    """
    result: dict[str, Any] = {}
    lines = fm_text.splitlines()
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        # Match a top-level key (no leading whitespace)
        m = re.match(r'^([A-Za-z_][\w-]*):\s*(.*)', line)
        if not m:
            i += 1
            continue

        key = m.group(1)
        raw = m.group(2).strip()
        i += 1

        # Inline list
        if raw.startswith("["):
            result[key] = _parse_inline_list(raw)
            continue

        # Non-empty scalar
        if raw:
            result[key] = _strip_quotes(raw)
            continue

        # Empty value — look ahead for block sequence or nested mapping
        sub_map: dict[str, Any] = {}
        seq: list = []

        while i < n:
            sub = lines[i]
            # Stop at next top-level key (no leading whitespace, matches key pattern)
            if sub and not sub[0].isspace():
                break

            if not sub.strip():
                # A blank line might terminate the block; peek ahead to see if
                # the next non-blank line is still indented (continuation) or top-level.
                i += 1
                # Peek: if next non-blank line is top-level, we're done
                j = i
                while j < n and not lines[j].strip():
                    j += 1
                if j < n and lines[j] and not lines[j][0].isspace():
                    break
                # else: blank line within an indented block — keep going
                continue

            # Block sequence item: starts with optional whitespace then "- "
            seq_m = re.match(r'^(\s+)- (.*)', sub)
            if seq_m:
                item_text = seq_m.group(2).strip()
                i += 1
                # Is this a mapping entry (history item)?  e.g. "at: ..."
                if re.match(r'^[A-Za-z_][\w-]*:\s', item_text) or item_text.endswith(':'):
                    entry: dict[str, str] = {}
                    em = re.match(r'^([A-Za-z_][\w-]*):\s*(.*)', item_text)
                    if em:
                        entry[em.group(1)] = _strip_quotes(em.group(2))
                    # Collect continuation lines (indented by more than the "- " line)
                    base_indent = len(seq_m.group(1)) + 2  # indent of the "- " plus 2
                    while i < n:
                        cont = lines[i]
                        if not cont.strip():
                            i += 1
                            break
                        cont_indent = len(cont) - len(cont.lstrip())
                        if cont_indent < base_indent:
                            break
                        cm = re.match(r'^\s+([A-Za-z_][\w-]*):\s*(.*)', cont)
                        if cm:
                            entry[cm.group(1)] = _strip_quotes(cm.group(2))
                        i += 1
                    seq.append(entry)
                else:
                    # Simple scalar sequence item
                    seq.append(_strip_quotes(item_text))
                continue

            # Nested mapping line: "  key: value"
            nm = re.match(r'^\s+([A-Za-z_][\w-]*):\s*(.*)', sub)
            if nm:
                sub_key = nm.group(1)
                sub_raw = nm.group(2).strip()
                if sub_raw.startswith("["):
                    sub_map[sub_key] = _parse_inline_list(sub_raw)
                else:
                    sub_map[sub_key] = _strip_quotes(sub_raw)
                i += 1
                continue

            # Unknown indented line — skip
            i += 1

        if seq:
            result[key] = seq
        elif sub_map:
            result[key] = sub_map
        else:
            result[key] = None

    return result


# ---------------------------------------------------------------------------
# Public: parse a single doc
# ---------------------------------------------------------------------------

def parse_doc(path: Path) -> dict:
    """
    Parse a live_docs markdown file and return a dict with:
      id, title, type, status, level, state
      depends_on  — list of id strings (may be empty)
      tags        — dict with keys 'domain' and 'scope' (each a list)
      created     — ISO 8601 string
      history     — list of {at, summary} dicts (may be empty)
      body        — the text after the closing '---'

    Fields not present in the file are absent from the dict (no defaults injected).
    The 'id' key is always set from the filename (authoritative); the frontmatter
    id is also parsed as 'id' and should match.
    """
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)

    if len(parts) < 3:
        # No valid frontmatter delimiters — return minimal dict
        return {"id": path.stem, "body": text}

    fm_raw = parts[1]
    body = parts[2].lstrip("\n")

    fm = _parse_frontmatter_text(fm_raw)

    # Normalize depends_on to always be a list
    dep = fm.get("depends_on")
    if dep is None:
        fm["depends_on"] = []
    elif isinstance(dep, str):
        # Scalar — shouldn't happen but handle gracefully
        fm["depends_on"] = [dep] if dep else []
    # else: already a list

    # Normalize references to always be a list (absent field → [], not an error)
    ref = fm.get("references")
    if ref is None:
        fm["references"] = []
    elif isinstance(ref, str):
        fm["references"] = [ref] if ref else []
    # else: already a list

    # Normalize history to always be a list
    hist = fm.get("history")
    if hist is None:
        fm["history"] = []
    elif not isinstance(hist, list):
        fm["history"] = []

    # Normalize tags to always be a dict with domain/scope lists
    tags = fm.get("tags")
    if not isinstance(tags, dict):
        fm["tags"] = {"domain": [], "scope": []}
    else:
        if not isinstance(tags.get("domain"), list):
            tags["domain"] = []
        if not isinstance(tags.get("scope"), list):
            tags["scope"] = []

    # Canonical id from filename (authoritative)
    fm["id"] = path.stem
    fm["body"] = body
    return fm


# ---------------------------------------------------------------------------
# Public: load all docs
# ---------------------------------------------------------------------------

def load_all(docs_dir: Path = DOCS_DIR) -> dict:
    """
    Load every *.md file in docs_dir (excluding .index/ subdirectory).

    Returns: {id: parsed_doc_dict}
    """
    result = {}
    for path in sorted(docs_dir.glob("*.md")):
        if ".index" in path.parts:
            continue
        doc = parse_doc(path)
        result[doc["id"]] = doc
    return result


# ---------------------------------------------------------------------------
# Public: graph helpers
# ---------------------------------------------------------------------------

def forward_edges(docs: dict) -> dict:
    """
    Build forward edge map: {id: [ids this doc depends_on]}.

    Only includes edges where the dependency id exists in docs (no dangling).
    """
    all_ids = set(docs.keys())
    fwd = {}
    for doc_id, doc in docs.items():
        deps = [d for d in doc.get("depends_on", []) if d in all_ids]
        fwd[doc_id] = deps
    return fwd


def reverse_edges(docs: dict) -> dict:
    """
    Build reverse edge map: {id: [ids that depend_on this id]}.

    Derived from forward_edges; never stored in files.
    """
    all_ids = set(docs.keys())
    rev: dict = {doc_id: [] for doc_id in all_ids}
    for doc_id, doc in docs.items():
        for dep_id in doc.get("depends_on", []):
            if dep_id in rev:
                rev[dep_id].append(doc_id)
    return rev


def dangling_edges(docs: dict) -> list:
    """
    Return list of (from_id, dep_id) tuples where dep_id does not exist in docs.

    Covers depends_on ONLY — this is the cascade graph.
    """
    all_ids = set(docs.keys())
    dangling = []
    for doc_id, doc in docs.items():
        for dep_id in doc.get("depends_on", []):
            if dep_id not in all_ids:
                dangling.append((doc_id, dep_id))
    return dangling


# ---------------------------------------------------------------------------
# References graph helpers — provenance/navigation ONLY, never cascade edges
# ---------------------------------------------------------------------------

def reference_edges(docs: dict) -> dict:
    """
    Build forward reference map: {id: [ids this doc references]}.

    This is a NAVIGATION artifact — provenance / "informed by" links.
    It must NEVER be used as cascade input; use forward_edges for that.
    Only includes entries where the referenced id exists in docs (no dangling).
    """
    all_ids = set(docs.keys())
    fwd = {}
    for doc_id, doc in docs.items():
        refs = [r for r in doc.get("references", []) if r in all_ids]
        fwd[doc_id] = refs
    return fwd


def referenced_by(docs: dict) -> dict:
    """
    Build reverse reference map: {id: [ids that reference this id]}.

    This is a NAVIGATION artifact — reverse provenance lookup.
    It must NEVER be used as cascade input; use reverse_edges for that.
    """
    all_ids = set(docs.keys())
    rev: dict = {doc_id: [] for doc_id in all_ids}
    for doc_id, doc in docs.items():
        for ref_id in doc.get("references", []):
            if ref_id in rev:
                rev[ref_id].append(doc_id)
    return rev


def dangling_references(docs: dict) -> list:
    """
    Return list of (from_id, ref_id) tuples where ref_id does not exist in docs.

    Covers references ONLY — NOT depends_on (use dangling_edges for that).
    """
    all_ids = set(docs.keys())
    dangling = []
    for doc_id, doc in docs.items():
        for ref_id in doc.get("references", []):
            if ref_id not in all_ids:
                dangling.append((doc_id, ref_id))
    return dangling


# ---------------------------------------------------------------------------
# Public: id → title map
# ---------------------------------------------------------------------------

def id_title_map(docs: dict) -> dict:
    """Return {id: title} for all docs."""
    return {doc_id: doc.get("title", doc_id) for doc_id, doc in docs.items()}
