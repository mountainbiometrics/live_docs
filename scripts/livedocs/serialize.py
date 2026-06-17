"""
serialize.py — Hand-rolled YAML parse + emit layer for live_docs.

Handles only the YAML shapes used by live_docs; no external dependencies.
Public API: parse_doc, dump_doc.
"""

import re
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Wikilink helpers for depends_on / references on-disk encoding
# ---------------------------------------------------------------------------

# Matches a bare wikilink id, e.g. [[20260616181728]] or [[20260616181728|alias]]
_WIKILINK_ID_RE = re.compile(r'^\[\[(\d{14})(?:\|[^\]]*)?\]\]$')


def _unwrap_wikilink(s: str) -> str:
    """Strip a '[[<id>]]' (or '[[<id>|alias]]') wrapper to the bare id.

    Passes through anything that does not match the wikilink pattern so that
    plain bare ids already stored on disk are returned unchanged.
    """
    m = _WIKILINK_ID_RE.match(s.strip()) if isinstance(s, str) else None
    return m.group(1) if m else s


def _yaml_wikilink_list(items: list) -> str:
    """Render a list of ids as quoted wikilinks for Obsidian compatibility.

    Example: ["[[20260616181728]]", "[[20260616181820]]"]
    Callers must guard against empty lists before calling (empty lists are
    omitted entirely on disk, not written as []).  Quoting is required —
    unquoted [[…]] inside an inline YAML list is ambiguous/invalid YAML.
    """
    inner = ", ".join(f'"[[{i}]]"' for i in items)
    return f"[{inner}]"


# ---------------------------------------------------------------------------
# Canonical field order
# ---------------------------------------------------------------------------

# Canonical order for ALL doc types (baseline)
# Spec: id, title, label, type, status, level, belongs_to, requires, relates,
#       provenance, superseded_by, tags, created, history
CANONICAL_FIELD_ORDER = [
    "id", "title", "label", "type", "status", "level",
    "belongs_to", "requires", "relates", "provenance", "superseded_by",
    "tags", "created", "history",
]

# Edge fields that use wikilink-wrapped lists on disk.
# These are omitted entirely when empty (not written as []).
EDGE_FIELDS = {"belongs_to", "requires", "relates", "provenance", "superseded_by"}

# Extra fields appended for reference docs (after canonical baseline)
REFERENCE_EXTRA_FIELDS = ["kind", "source", "imported"]


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
    - Block sequences:  key:\\n  - item     (simple strings)
    - History blocks:   history:\\n  - at: "..."\\n    summary: "..."
    - Nested mappings:  tags:\\n  domain: []\\n  scope: [live_docs]
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

def _normalize_edge_field(fm: dict, key: str) -> None:
    """
    Normalize a wikilink-list edge field in-place.

    On-disk values may be wrapped as "[[<id>]]" (wikilink form for Obsidian);
    _unwrap_wikilink strips that wrapper so the in-memory model uses plain ids.
    Absent field stays absent (no empty list injected) — absence == [] downstream.
    """
    val = fm.get(key)
    if val is None:
        # Field absent — leave absent; callers use .get(key, [])
        return
    if isinstance(val, str):
        fm[key] = [_unwrap_wikilink(val)] if val else []
    else:
        fm[key] = [_unwrap_wikilink(v) for v in val]


def parse_doc(path: Path) -> dict:
    """
    Parse a live_docs markdown file and return a dict with:
      id, title, label, type, status, level
      belongs_to    — list of id strings (absent if empty; use .get(k, []))
      requires      — list of id strings (absent if empty)
      relates       — list of id strings (absent if empty)
      provenance    — list of id strings (absent if empty)
      superseded_by — list of id strings (absent if empty)
      tags          — dict with keys 'domain' and 'scope' (each a list)
      created       — ISO 8601 string
      history       — list of {at, summary} dicts (may be empty list or absent)
      body          — the text after the closing '---'

    Old field names (depends_on, references, state) are tolerated on read and
    normalised transparently: depends_on → requires, references → provenance,
    state is kept as-is (validate will warn; doc migration removes it).

    Fields not present in the file are absent from the dict (no defaults injected).
    The 'id' key is always set from the filename (authoritative).
    """
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)

    if len(parts) < 3:
        # No valid frontmatter delimiters — return minimal dict
        return {"id": path.stem, "body": text}

    fm_raw = parts[1]
    body = parts[2].lstrip("\n")

    fm = _parse_frontmatter_text(fm_raw)

    # --- Transparent backward-compat aliases (old field names) ---
    # depends_on → requires (if requires not already present)
    if "depends_on" in fm and "requires" not in fm:
        fm["requires"] = fm.pop("depends_on")
    elif "depends_on" in fm:
        fm.pop("depends_on")  # discard old name if new one already present

    # references → provenance (if provenance not already present)
    if "references" in fm and "provenance" not in fm:
        fm["provenance"] = fm.pop("references")
    elif "references" in fm:
        fm.pop("references")

    # Normalize all edge fields (wikilink unwrap; absent stays absent)
    for edge_key in ("belongs_to", "requires", "relates", "provenance", "superseded_by"):
        _normalize_edge_field(fm, edge_key)

    # Normalize history to always be a list (absent → leave absent OR normalize to [])
    hist = fm.get("history")
    if hist is None:
        # absent — leave absent; callers do fm.get("history", [])
        pass
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
# YAML emission helpers (hand-rolled — no pyyaml)
# ---------------------------------------------------------------------------

def _yaml_str(value: str) -> str:
    """Wrap a string value in double-quotes, escaping inner quotes."""
    escaped = str(value).replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def _yaml_list(items: list) -> str:
    """Render a list inline, e.g. [live_docs, sinai]."""
    if not items:
        return "[]"
    inner = ", ".join(str(i) for i in items)
    return f"[{inner}]"


def _emit_field(key: str, value: Any) -> list[str]:
    """
    Render a single frontmatter key/value pair to YAML lines.

    Handles: str scalars, list (inline or block sequence for history),
    dict (nested mapping for tags), None → omitted.

    Empty-list omission rules:
    - Edge fields (belongs_to, requires, relates, provenance, superseded_by):
      omitted entirely when empty.
    - history: omitted entirely when empty.
    - tags: omitted when both domain and scope are empty.
    """
    if value is None:
        return []

    # Tags: nested mapping — omit entirely when both domain and scope are empty
    if key == "tags" and isinstance(value, dict):
        domain = value.get("domain", [])
        scope = value.get("scope", [])
        if not domain and not scope:
            return []
        lines = ["tags:"]
        lines.append(f"  domain: {_yaml_list(domain)}")
        lines.append(f"  scope: {_yaml_list(scope)}")
        return lines

    # History: block sequence of mappings — omit entirely when empty
    if key == "history" and isinstance(value, list):
        if not value:
            return []
        lines = ["history:"]
        for entry in value:
            at = entry.get("at", "")
            summary = entry.get("summary", "")
            lines.append(f"  - at: {_yaml_str(at)}")
            lines.append(f"    summary: {_yaml_str(summary)}")
        return lines

    # Edge fields: wikilink-wrapped inline list for Obsidian graph.
    # Omitted entirely when empty — callers should not pass empty lists here,
    # but guard defensively.
    if key in EDGE_FIELDS and isinstance(value, list):
        if not value:
            return []
        return [f"{key}: {_yaml_wikilink_list(value)}"]

    # Other lists: inline
    if isinstance(value, list):
        return [f"{key}: {_yaml_list(value)}"]

    # Scalar — use quoted string for everything except simple unquoted values
    # (We quote all scalar values for consistency and safety.)
    if isinstance(value, str):
        # Unquoted for type/status/level/kind values (simple identifiers)
        if key in ("type", "status", "level", "kind") and value and \
                re.match(r'^[a-z][a-z0-9_-]*$', value):
            return [f"{key}: {value}"]
        return [f"{key}: {_yaml_str(value)}"]

    return [f"{key}: {value}"]


def dump_doc(frontmatter: dict, body: str) -> str:
    """
    Serialize a doc back to its on-disk format.

    Emits frontmatter fields in canonical order:
      id, title, label, type, status, level,
      belongs_to, requires, relates, provenance, superseded_by,
      tags, created, history
    Then appends reference-type extras (kind, source, imported) if present.

    Empty-list edge fields (belongs_to, requires, relates, provenance,
    superseded_by) and empty history are omitted entirely.
    Tags are omitted when both domain and scope are empty.

    Body is preserved byte-for-byte; only the frontmatter block is reconstructed.
    Returns the full file text ready to write.
    """
    lines = ["---"]

    # Determine which extra fields this doc has beyond the baseline
    doc_type = frontmatter.get("type", "")
    if doc_type == "reference":
        ordered_keys = CANONICAL_FIELD_ORDER + REFERENCE_EXTRA_FIELDS
    else:
        ordered_keys = CANONICAL_FIELD_ORDER

    # Emit canonical fields
    seen = set()
    for key in ordered_keys:
        if key not in frontmatter:
            continue
        seen.add(key)
        lines.extend(_emit_field(key, frontmatter[key]))

    # Emit any extra fields not in the canonical order (preserve them)
    for key, value in frontmatter.items():
        if key in seen or key in ("body",):
            continue
        lines.extend(_emit_field(key, value))

    lines.append("---")

    fm_block = "\n".join(lines)

    # Body: preserve byte-for-byte; ensure file ends with newline
    if body:
        text = fm_block + "\n\n" + body
    else:
        text = fm_block + "\n"

    if not text.endswith("\n"):
        text += "\n"

    return text
