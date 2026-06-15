"""
livedocs.py — Shared library for the live_docs tooling.

Stdlib only (pathlib, re, datetime). No external dependencies. Import from other scripts:

    from livedocs import DOCS_DIR, RAW_DIR, parse_doc, load_all, forward_edges, reverse_edges, id_title_map, generate_id, KB

Repo-root detection: the repo root is the parent of the directory that
contains this file (scripts/ → repo root). This works regardless of CWD.
"""

import json
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
TEMPLATES_DIR: Path = REPO_ROOT / "templates"


# ---------------------------------------------------------------------------
# Canonical field order
# ---------------------------------------------------------------------------

# Canonical order for ALL doc types (baseline)
CANONICAL_FIELD_ORDER = [
    "id", "title", "slug", "type", "status", "level", "state",
    "depends_on", "references", "tags", "created", "history",
]

# Extra fields appended for reference docs (after canonical baseline)
REFERENCE_EXTRA_FIELDS = ["kind", "source", "imported"]

# Valid enum values
VALID_TYPES = {
    "type", "principle", "goal", "decision", "constraint",
    "requirement", "use-case", "guide", "component", "reference", "index",
}
VALID_STATUSES = {"living", "historical"}
VALID_LEVELS = {"incidental", "trial", "preference", "requirement"}
VALID_STATES = {"actual", "target"}
VALID_REFERENCE_KINDS = {"brainstorm", "plan", "clipping", "external"}

# Slug validation pattern
SLUG_RE = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')


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

def parse_doc(path: Path) -> dict:
    """
    Parse a live_docs markdown file and return a dict with:
      id, title, slug, type, status, level, state
      depends_on  — list of id strings (may be empty)
      references  — list of id strings (may be empty)
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
    """
    if value is None:
        return []

    # Tags: nested mapping
    if key == "tags" and isinstance(value, dict):
        lines = ["tags:"]
        domain = value.get("domain", [])
        scope = value.get("scope", [])
        lines.append(f"  domain: {_yaml_list(domain)}")
        lines.append(f"  scope: {_yaml_list(scope)}")
        return lines

    # History: block sequence of mappings
    if key == "history" and isinstance(value, list):
        if not value:
            return ["history: []"]
        lines = ["history:"]
        for entry in value:
            at = entry.get("at", "")
            summary = entry.get("summary", "")
            lines.append(f"  - at: {_yaml_str(at)}")
            lines.append(f"    summary: {_yaml_str(summary)}")
        return lines

    # depends_on / references: inline list
    if key in ("depends_on", "references") and isinstance(value, list):
        return [f"{key}: {_yaml_list(value)}"]

    # Other lists: inline
    if isinstance(value, list):
        return [f"{key}: {_yaml_list(value)}"]

    # Scalar — use quoted string for everything except simple unquoted values
    # (We quote all scalar values for consistency and safety.)
    if isinstance(value, str):
        # Unquoted for type/status/level/state/kind values (simple identifiers)
        # to match existing style
        if key in ("type", "status", "level", "state", "kind") and value and \
                re.match(r'^[a-z][a-z0-9_-]*$', value):
            return [f"{key}: {value}"]
        return [f"{key}: {_yaml_str(value)}"]

    return [f"{key}: {value}"]


def dump_doc(frontmatter: dict, body: str) -> str:
    """
    Serialize a doc back to its on-disk format.

    Emits frontmatter fields in canonical order (id, title, slug, type, status,
    level, state, depends_on, references, tags, created, history), then appends
    reference-type extras (kind, source, imported) if present.

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


# ---------------------------------------------------------------------------
# Slug generation utilities
# ---------------------------------------------------------------------------

def title_to_slug(title: str) -> str:
    """
    Convert a title to a kebab-case slug.

    Rules:
    - Lowercase everything
    - Replace non-alphanumeric runs with a single hyphen
    - Strip leading/trailing hyphens
    - Truncate to 60 chars at a word boundary
    """
    s = title.lower()
    # Remove common leading patterns like "Type: " or "Reference: "
    s = re.sub(r'^type:\s*', 'type-', s)
    s = re.sub(r'^reference:\s*', '', s)
    # Replace non-alphanumeric with hyphens
    s = re.sub(r'[^a-z0-9]+', '-', s)
    # Strip leading/trailing hyphens
    s = s.strip('-')
    # Truncate at ~60 chars at a word boundary (hyphen)
    if len(s) > 60:
        s = s[:61].rsplit('-', 1)[0]
    s = s.strip('-')
    return s


def unique_slug(base: str, existing_slugs: set[str]) -> str:
    """Return base slug, appending -2, -3, etc. until unique."""
    slug = base
    n = 2
    while slug in existing_slugs:
        slug = f"{base}-{n}"
        n += 1
    return slug


# ---------------------------------------------------------------------------
# KB class — unified store API
# ---------------------------------------------------------------------------

class KB:
    """
    Unified query/mutation layer over the live_docs store.

    All ref arguments accept: doc id, slug, exact title, or unique case-insensitive
    title substring. Resolution order: id → slug → exact title → unique substring.

    Mutators are DUMB: they write what you tell them; no cascade judgment here.
    Skills handle cascade decisions.
    """

    def __init__(self, docs_dir: Path = DOCS_DIR):
        self.docs_dir = docs_dir
        self._reload()

    def _reload(self) -> None:
        """(Re)load all docs from disk."""
        self._docs = load_all(self.docs_dir)

    # -----------------------------------------------------------------------
    # Resolution
    # -----------------------------------------------------------------------

    def resolve(self, ref: str) -> str:
        """
        Resolve a ref (id, slug, exact title, or unique title substring) to an id.

        Resolution order:
          1. Exact id match
          2. Exact slug match
          3. Exact title match (case-insensitive)
          4. Unique case-insensitive title substring

        Raises ValueError if ambiguous or not found.
        """
        docs = self._docs
        ref_lower = ref.lower()

        # 1. Exact id
        if ref in docs:
            return ref

        # 2. Exact slug
        for doc_id, doc in docs.items():
            if doc.get("slug", "") == ref:
                return doc_id

        # 3. Exact title (case-insensitive)
        exact = [
            doc_id for doc_id, doc in docs.items()
            if doc.get("title", "").lower() == ref_lower
        ]
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            candidates = [f"{d} ({docs[d].get('title','')})" for d in exact]
            raise ValueError(
                f"Ambiguous ref {ref!r} — multiple exact title matches:\n" +
                "\n".join(f"  {c}" for c in candidates)
            )

        # 4. Unique case-insensitive substring
        partial = [
            doc_id for doc_id, doc in docs.items()
            if ref_lower in doc.get("title", "").lower()
        ]
        if len(partial) == 1:
            return partial[0]
        if len(partial) > 1:
            candidates = [f"{d} ({docs[d].get('title','')})" for d in partial]
            raise ValueError(
                f"Ambiguous ref {ref!r} — multiple title substring matches:\n" +
                "\n".join(f"  {c}" for c in candidates)
            )

        raise ValueError(f"No doc found for ref: {ref!r}")

    def label(self, doc_id: str) -> str:
        """Return '<Type>: <Title>' label for a doc id."""
        doc = self._docs.get(doc_id, {})
        t = doc.get("type", "?")
        title = doc.get("title", doc_id)
        return f"{t.capitalize()}: {title}"

    def _edge_list(self, ids: list[str]) -> list[dict]:
        """Convert a list of ids to [{id, slug, label}] dicts."""
        result = []
        for eid in ids:
            doc = self._docs.get(eid, {})
            result.append({
                "id": eid,
                "slug": doc.get("slug", ""),
                "label": self.label(eid) if eid in self._docs else f"(missing) {eid}",
            })
        return result

    # -----------------------------------------------------------------------
    # Reads
    # -----------------------------------------------------------------------

    def get(self, ref: str) -> dict:
        """
        Return {id, label, slug, frontmatter, body} for the resolved doc.
        """
        doc_id = self.resolve(ref)
        doc = self._docs[doc_id]
        fm = {k: v for k, v in doc.items() if k != "body"}
        return {
            "id": doc_id,
            "label": self.label(doc_id),
            "slug": doc.get("slug", ""),
            "frontmatter": fm,
            "body": doc.get("body", ""),
        }

    def body(self, ref: str) -> str:
        """Return just the body text of the resolved doc."""
        doc_id = self.resolve(ref)
        return self._docs[doc_id].get("body", "")

    def show(self, ref: str) -> dict:
        """
        Return full doc info including resolved edges.

        depends_on, references, dependents, referenced_by each rendered as
        [{id, slug, label}] rather than bare id lists.
        """
        doc_id = self.resolve(ref)
        doc = self._docs[doc_id]
        fm = {k: v for k, v in doc.items() if k != "body"}

        # Build reverse maps
        rev = reverse_edges(self._docs)
        ref_by = referenced_by(self._docs)

        return {
            "id": doc_id,
            "label": self.label(doc_id),
            "slug": doc.get("slug", ""),
            "frontmatter": fm,
            "body": doc.get("body", ""),
            "depends_on": self._edge_list(doc.get("depends_on", [])),
            "references": self._edge_list(doc.get("references", [])),
            "dependents": self._edge_list(rev.get(doc_id, [])),
            "referenced_by": self._edge_list(ref_by.get(doc_id, [])),
        }

    def find(
        self,
        query: str = None,
        type: str = None,
        level: str = None,
        state: str = None,
        status: str = None,
        scope: str = None,
        domain: str = None,
    ) -> list[dict]:
        """
        Search docs with optional filters. Returns [{id, slug, label, snippet}].

        query matches title + slug + body (case-insensitive).
        All other args filter by frontmatter field values.
        """
        results = []
        q = query.lower() if query else None

        for doc_id, doc in sorted(self._docs.items()):
            # Filter checks
            if type and doc.get("type") != type:
                continue
            if level and doc.get("level") != level:
                continue
            if state and doc.get("state") != state:
                continue
            if status and doc.get("status") != status:
                continue

            tags = doc.get("tags", {})
            if scope:
                if scope not in tags.get("scope", []):
                    continue
            if domain:
                if domain not in tags.get("domain", []):
                    continue

            # Query match
            snippet = ""
            if q:
                title = doc.get("title", "").lower()
                slug = doc.get("slug", "").lower()
                body = doc.get("body", "").lower()
                if q in title or q in slug or q in body:
                    # Build snippet from first matching body line
                    for line in doc.get("body", "").splitlines():
                        if q in line.lower():
                            snippet = line.strip()[:120]
                            break
                    if not snippet and q in doc.get("title", "").lower():
                        snippet = doc.get("title", "")[:120]
                else:
                    continue

            results.append({
                "id": doc_id,
                "slug": doc.get("slug", ""),
                "label": self.label(doc_id),
                "snippet": snippet,
            })

        return results

    def ls(self, type: str = None) -> list[dict]:
        """List all docs. Returns [{id, slug, label}]."""
        results = []
        for doc_id, doc in sorted(self._docs.items()):
            if type and doc.get("type") != type:
                continue
            results.append({
                "id": doc_id,
                "slug": doc.get("slug", ""),
                "label": self.label(doc_id),
            })
        return results

    # -----------------------------------------------------------------------
    # Graph
    # -----------------------------------------------------------------------

    def neighbors(self, ref: str, kind: str = "all") -> dict:
        """
        Return neighbor edge lists for ref.

        kind: 'depends_on' | 'references' | 'dependents' | 'referenced_by' | 'all'
        Returns dict with requested edge lists as [{id, slug, label}].
        """
        doc_id = self.resolve(ref)
        doc = self._docs[doc_id]

        rev = reverse_edges(self._docs)
        ref_by = referenced_by(self._docs)

        result = {}
        if kind in ("depends_on", "all"):
            result["depends_on"] = self._edge_list(doc.get("depends_on", []))
        if kind in ("references", "all"):
            result["references"] = self._edge_list(doc.get("references", []))
        if kind in ("dependents", "all"):
            result["dependents"] = self._edge_list(rev.get(doc_id, []))
        if kind in ("referenced_by", "all"):
            result["referenced_by"] = self._edge_list(ref_by.get(doc_id, []))

        return result

    def graph(self, ref: str, depth: int = 1, direction: str = "both") -> dict:
        """
        BFS traversal over depends_on edges only (references are NOT graph edges).

        direction: 'up' (follow depends_on), 'down' (follow dependents), 'both'
        Returns {nodes: [{id, slug, label, depth}], edges: [[from_id, to_id], ...]}
        """
        root_id = self.resolve(ref)
        fwd = forward_edges(self._docs)
        rev = reverse_edges(self._docs)

        visited: dict[str, int] = {}  # id → depth
        queue = [(root_id, 0)]
        edges: list[list[str]] = []

        while queue:
            node_id, d = queue.pop(0)
            if node_id in visited:
                continue
            visited[node_id] = d

            if d >= depth:
                continue

            if direction in ("up", "both"):
                for dep_id in fwd.get(node_id, []):
                    edges.append([node_id, dep_id])
                    if dep_id not in visited:
                        queue.append((dep_id, d + 1))

            if direction in ("down", "both"):
                for dep_id in rev.get(node_id, []):
                    edges.append([dep_id, node_id])
                    if dep_id not in visited:
                        queue.append((dep_id, d + 1))

        nodes = [
            {
                "id": nid,
                "slug": self._docs.get(nid, {}).get("slug", ""),
                "label": self.label(nid) if nid in self._docs else f"(missing) {nid}",
                "depth": d,
            }
            for nid, d in sorted(visited.items(), key=lambda x: (x[1], x[0]))
        ]

        return {"nodes": nodes, "edges": edges}

    # -----------------------------------------------------------------------
    # Mutators (DUMB — no cascade/dedup; skills decide that)
    # -----------------------------------------------------------------------

    def _load_doc_raw(self, doc_id: str) -> tuple[dict, str]:
        """Load a doc from disk, return (frontmatter_dict, body_str)."""
        path = self.docs_dir / f"{doc_id}.md"
        doc = parse_doc(path)
        body = doc.pop("body", "")
        return doc, body

    def _write_doc(self, doc_id: str, fm: dict, body: str) -> None:
        """Write a doc to disk using canonical dump_doc, then reload."""
        path = self.docs_dir / f"{doc_id}.md"
        path.write_text(dump_doc(fm, body), encoding="utf-8")
        self._reload()

    def new(
        self,
        type: str,
        title: str,
        slug: str = "",
        level: str = "incidental",
        state: str = "actual",
        status: str = "living",
        depends_on: list[str] = None,
        references: list[str] = None,
        tags_domain: list[str] = None,
        tags_scope: list[str] = None,
        body: str = "",
        # reference-type extras
        kind: str = "",
        source: str = "",
    ) -> str:
        """
        Create a new doc. Returns the new doc id.

        depends_on and references accept ids, slugs, or titles — resolved via resolve().
        """
        from datetime import datetime, timezone

        doc_id = generate_id(self.docs_dir)
        created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Resolve edge refs to ids
        dep_ids = [self.resolve(r) for r in (depends_on or [])]
        ref_ids = [self.resolve(r) for r in (references or [])]

        # Generate slug if not provided
        if not slug:
            existing = {d.get("slug", "") for d in self._docs.values()}
            slug = unique_slug(title_to_slug(title), existing)

        fm: dict[str, Any] = {
            "id": doc_id,
            "title": title,
            "slug": slug,
            "type": type,
            "status": status,
            "level": level,
            "state": state,
            "depends_on": dep_ids,
            "references": ref_ids,
            "tags": {
                "domain": list(tags_domain or []),
                "scope": list(tags_scope or []),
            },
            "created": created,
            "history": [],
        }

        if type == "reference":
            fm["kind"] = kind or "clipping"
            fm["source"] = source
            fm["imported"] = created

        path = self.docs_dir / f"{doc_id}.md"
        path.write_text(dump_doc(fm, body), encoding="utf-8")
        self._reload()
        return doc_id

    def set(self, ref: str, **fields) -> None:
        """
        Update scalar frontmatter fields: title, slug, level, state, status, type.

        Resolves ref, loads doc, updates fields, writes back.
        """
        allowed = {"title", "slug", "level", "state", "status", "type"}
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"set() does not accept fields: {unknown}. Allowed: {allowed}")

        doc_id = self.resolve(ref)
        fm, body = self._load_doc_raw(doc_id)
        for k, v in fields.items():
            fm[k] = v
        self._write_doc(doc_id, fm, body)

    def link(self, ref: str, depends_on: list[str] = None, references: list[str] = None) -> None:
        """
        Add edges. Deduplicates; does NOT remove existing edges.

        All ref args resolved via resolve().
        """
        doc_id = self.resolve(ref)
        fm, body = self._load_doc_raw(doc_id)

        if depends_on:
            existing = set(fm.get("depends_on", []))
            for r in depends_on:
                existing.add(self.resolve(r))
            fm["depends_on"] = sorted(existing)

        if references:
            existing = set(fm.get("references", []))
            for r in references:
                existing.add(self.resolve(r))
            fm["references"] = sorted(existing)

        self._write_doc(doc_id, fm, body)

    def unlink(self, ref: str, depends_on: list[str] = None, references: list[str] = None) -> None:
        """
        Remove edges.

        All ref args resolved via resolve().
        """
        doc_id = self.resolve(ref)
        fm, body = self._load_doc_raw(doc_id)

        if depends_on:
            remove = {self.resolve(r) for r in depends_on}
            fm["depends_on"] = [i for i in fm.get("depends_on", []) if i not in remove]

        if references:
            remove = {self.resolve(r) for r in references}
            fm["references"] = [i for i in fm.get("references", []) if i not in remove]

        self._write_doc(doc_id, fm, body)

    def add_history(self, ref: str, summary: str) -> None:
        """Append a history entry {at: <utc iso>, summary: <summary>}."""
        doc_id = self.resolve(ref)
        fm, body = self._load_doc_raw(doc_id)

        at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        hist = fm.get("history", [])
        if not isinstance(hist, list):
            hist = []
        hist.append({"at": at, "summary": summary})
        fm["history"] = hist

        self._write_doc(doc_id, fm, body)

    def ingest_raw(
        self,
        source: str,
        body: str = "",
        from_file: str = "",
        title: str = "",
        slug: str = "",
    ) -> str:
        """
        Write verbatim content into raw/ tier. Returns the raw id.

        Mirrors ingest_raw.py behavior but operates through KB.
        """
        from datetime import date

        RAW_DIR.mkdir(parents=True, exist_ok=True)
        raw_id = generate_id(RAW_DIR)
        imported = date.today().strftime("%Y-%m-%d")

        if from_file:
            p = Path(from_file)
            if not p.exists():
                raise FileNotFoundError(f"--from-file path does not exist: {p}")
            body = p.read_text(encoding="utf-8")

        lines = ["---", f"id: {_yaml_str(raw_id)}"]
        if title:
            lines.append(f"title: {_yaml_str(title)}")
        lines += [
            "type: reference",
            "kind: clipping",
            "status: historical",
            f"original_source: {_yaml_str(source)}",
            f"imported: {_yaml_str(imported)}",
            "---",
        ]
        fm_block = "\n".join(lines)
        content = fm_block + "\n\n" + body
        if not content.endswith("\n"):
            content += "\n"

        out = RAW_DIR / f"{raw_id}.md"
        out.write_text(content, encoding="utf-8")
        return raw_id

    def delete(self, doc_id: str) -> None:
        """Delete a doc by id. Use only for throwaway/test docs."""
        path = self.docs_dir / f"{doc_id}.md"
        if path.exists():
            path.unlink()
        self._reload()
