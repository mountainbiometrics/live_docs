"""
kb.py — KB class and load_all: unified store API for live_docs.

KB wraps parse, serialize, graph, and model helpers into a single query/mutation
layer. Mutators are DUMB: they write what you tell them; no cascade judgment here.
Stdlib only. No external dependencies.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .model import (
    DOCS_DIR, RAW_DIR,
    generate_id, title_to_label, unique_label, display_label,
)
from .serialize import parse_doc, dump_doc, _yaml_str
from .graph import reverse_edges, referenced_by, forward_edges, relates_edges, superseded_by_edges


# ---------------------------------------------------------------------------
# Tag access — flat top-level domain/scope
# ---------------------------------------------------------------------------

def _doc_tag_list(doc: dict, key: str) -> list:
    """Return a doc's `domain` or `scope` list from the flat top-level field."""
    flat = doc.get(key)
    return flat if isinstance(flat, list) else []


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
# KB class — unified store API
# ---------------------------------------------------------------------------

class KB:
    """
    Unified query/mutation layer over the live_docs store.

    All ref arguments accept: doc id, label, exact title, or unique case-insensitive
    substring of title or label. Resolution order: id → exact label (case-insensitive)
    → exact title → unique case-insensitive substring of title or label.

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
        Resolve a ref to an id.

        A ref may be: an id, a label, an exact title, or a unique
        case-insensitive substring of a title or label.

        Resolution order:
          1. Exact id match
          2. Exact label match (case-insensitive)
          3. Exact title match (case-insensitive)
          4. Unique case-insensitive substring of title OR label

        Raises ValueError if ambiguous or not found.
        """
        docs = self._docs
        ref_lower = ref.lower()

        # 1. Exact id
        if ref in docs:
            return ref

        # 2. Exact label (case-insensitive)
        label_matches = [
            doc_id for doc_id, doc in docs.items()
            if doc.get("label", "").lower() == ref_lower
        ]
        if len(label_matches) == 1:
            return label_matches[0]
        if len(label_matches) > 1:
            candidates = [f"{d} ({docs[d].get('title','')})" for d in label_matches]
            raise ValueError(
                f"Ambiguous ref {ref!r} — multiple exact label matches:\n" +
                "\n".join(f"  {c}" for c in candidates)
            )

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

        # 4. Unique case-insensitive substring of title OR label
        partial = [
            doc_id for doc_id, doc in docs.items()
            if ref_lower in doc.get("title", "").lower()
            or ref_lower in doc.get("label", "").lower()
        ]
        if len(partial) == 1:
            return partial[0]
        if len(partial) > 1:
            candidates = [f"{d} ({docs[d].get('title','')})" for d in partial]
            raise ValueError(
                f"Ambiguous ref {ref!r} — multiple title/label substring matches:\n" +
                "\n".join(f"  {c}" for c in candidates)
            )

        raise ValueError(f"No doc found for ref: {ref!r}")

    def display_label(self, doc_id: str) -> str:
        """Return '<Type>: <Title>' display string for a doc id."""
        return display_label(self._docs.get(doc_id, {"id": doc_id}))

    def _edge_list(self, ids: list[str]) -> list[dict]:
        """
        Convert a list of ids to [{id, label, display}] dicts.

        `label` is the doc's frontmatter label; `display` is the
        '<Type>: <Title>' string used for human-readable rendering.
        """
        result = []
        for eid in ids:
            doc = self._docs.get(eid, {})
            result.append({
                "id": eid,
                "label": doc.get("label", ""),
                "display": self.display_label(eid) if eid in self._docs else f"(missing) {eid}",
            })
        return result

    # -----------------------------------------------------------------------
    # Reads
    # -----------------------------------------------------------------------

    def get(self, ref: str) -> dict:
        """
        Return {id, label, display, frontmatter, body} for the resolved doc.
        """
        doc_id = self.resolve(ref)
        doc = self._docs[doc_id]
        fm = {k: v for k, v in doc.items() if k != "body"}
        return {
            "id": doc_id,
            "label": doc.get("label", ""),
            "display": self.display_label(doc_id),
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

        requires, belongs_to, relates, provenance, superseded_by are rendered
        as [{id, label, display}] lists.  Reverse cascade edges (dependents)
        and reverse provenance (provenance_of) are also included.
        """
        doc_id = self.resolve(ref)
        doc = self._docs[doc_id]
        fm = {k: v for k, v in doc.items() if k != "body"}

        # Build reverse maps
        rev = reverse_edges(self._docs)
        ref_by = referenced_by(self._docs)

        return {
            "id": doc_id,
            "label": doc.get("label", ""),
            "display": self.display_label(doc_id),
            "frontmatter": fm,
            "body": doc.get("body", ""),
            # Forward edges
            "requires": self._edge_list(doc.get("requires", [])),
            "belongs_to": self._edge_list(doc.get("belongs_to", [])),
            "relates": self._edge_list(doc.get("relates", [])),
            "provenance": self._edge_list(doc.get("provenance", [])),
            "superseded_by": self._edge_list(doc.get("superseded_by", [])),
            # Reverse edges
            "dependents": self._edge_list(rev.get(doc_id, [])),
            "provenance_of": self._edge_list(ref_by.get(doc_id, [])),
            # Topological facet: union of `scope` anchors along the belongs_to
            # genealogy (own scope included). Read off topology, not stored.
            "effective_scope": self.effective_scope(doc_id),
        }

    def effective_scope(self, ref: str) -> list[str]:
        """
        Return a doc's EFFECTIVE scope: the union of `scope` anchor values along
        its WHOLE `belongs_to` genealogy — every belongs_to ancestor, plus the
        doc's own `scope` if set.

        Computed over `belongs_to` ONLY (never `requires`): per the reframe,
        belonging confers lineage/scope while requiring does not. The walk is
        cycle-defensive — a `belongs_to` cycle (which validate now rejects as a
        hard error) cannot make this loop forever.

        Returns a sorted list of distinct scope strings (empty if no anchor in
        the genealogy sets a scope).
        """
        start = self.resolve(ref)
        scopes: set[str] = set()
        seen: set[str] = set()
        stack = [start]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            doc = self._docs.get(current)
            if not doc:
                continue
            sc = doc.get("scope")
            if isinstance(sc, str) and sc.strip():
                scopes.add(sc.strip())
            elif isinstance(sc, list):
                # tolerate any legacy list value
                scopes.update(s.strip() for s in sc if isinstance(s, str) and s.strip())
            for parent in doc.get("belongs_to", []):
                if parent not in seen:
                    stack.append(parent)
        return sorted(scopes)

    def find(
        self,
        query: str | None = None,
        type: str | None = None,
        level: str | None = None,
        status: str | None = None,
        scope: str | None = None,
        domain: str | None = None,
        terms: list[str] | None = None,
        or_mode: bool = False,
        regex: str | None = None,
    ) -> list[dict]:
        """
        Search docs with optional filters. Returns [{id, label, display, snippet}].

        query       — single query string; matches title + label + body (case-insensitive).
        terms       — list of query strings; in AND mode (default) all must match;
                      in OR mode (or_mode=True) any match is sufficient.
        or_mode     — when True, combine `terms` with OR logic instead of AND.
        regex       — a regex pattern applied to title + label + body (re.IGNORECASE).

        All other args filter by frontmatter field values.
        Multiple query mechanisms (query / terms / regex) are AND-combined with each other.
        """
        results = []

        # Build query matchers
        # Single `query` → convert to single-term list (AND with `terms`)
        all_terms: list[str] = []
        if query:
            all_terms.append(query.lower())
        if terms:
            all_terms.extend(t.lower() for t in terms if t)

        compiled_regex = None
        if regex:
            try:
                compiled_regex = re.compile(regex, re.IGNORECASE)
            except re.error as exc:
                raise ValueError(f"Invalid regex pattern {regex!r}: {exc}") from exc

        for doc_id, doc in sorted(self._docs.items()):
            # Metadata filters
            if type and doc.get("type") != type:
                continue
            if level and doc.get("level") != level:
                continue
            if status and doc.get("status") != status:
                continue

            doc_domain = _doc_tag_list(doc, "domain")
            # scope is now a single string naming a topological zone; match the
            # filter against the doc's EFFECTIVE scope (own + belongs_to ancestry)
            # so a scope query finds the whole subtree, not just hand-stamped docs.
            if scope and scope not in self.effective_scope(doc_id):
                continue
            if domain and domain not in doc_domain:
                continue

            # Build searchable text fields
            title_lower = doc.get("title", "").lower()
            label_lower = doc.get("label", "").lower()
            body_raw = doc.get("body", "")
            body_lower = body_raw.lower()

            def _first_snippet(term: str) -> str:
                """Return first matching body line snippet for a term."""
                for line in body_raw.splitlines():
                    if term in line.lower():
                        return line.strip()[:120]
                return ""

            snippet = ""

            # Term matching
            if all_terms:
                def _term_hits(t: str) -> bool:
                    return t in title_lower or t in label_lower or t in body_lower

                if or_mode:
                    if not any(_term_hits(t) for t in all_terms):
                        continue
                    for t in all_terms:
                        if _term_hits(t):
                            snippet = _first_snippet(t) or doc.get("title", "")[:120]
                            break
                else:
                    # AND: every term must match somewhere
                    if not all(_term_hits(t) for t in all_terms):
                        continue
                    snippet = _first_snippet(all_terms[0]) or doc.get("title", "")[:120]

            # Regex matching
            if compiled_regex:
                combined = f"{doc.get('title','')} {doc.get('label','')} {body_raw}"
                if not compiled_regex.search(combined):
                    continue
                # Extract snippet from first regex match in body
                m = compiled_regex.search(body_raw)
                if m and not snippet:
                    start = max(0, m.start() - 20)
                    snippet = body_raw[start:m.end() + 60].strip()[:120]

            results.append({
                "id": doc_id,
                "label": doc.get("label", ""),
                "display": self.display_label(doc_id),
                "snippet": snippet,
            })

        return results

    def orphans(self) -> list[dict]:
        """
        Return docs that sit OUTSIDE the belongs_to hierarchy entirely.

        Canonical, single-source definition (pure topology, navigability-based):
        a doc is an orphan iff it has NO `belongs_to` edge in EITHER direction —
        no `belongs_to` parent (outbound) AND nothing `belongs_to`s it (no
        descendants, inbound). It is unreachable through the navigational
        hierarchy.

        `requires` / `relates` / `provenance` / `superseded_by` are NOT hierarchy
        and do NOT count. There are NO type-based exemptions here — consumers
        (garden, the viewer) apply their own judgment (e.g. skip frozen/reference
        docs) on top of this raw topology.

        This is the authoritative orphan computation. It is intentionally NOT a
        derived cache: callers query it FRESH (cf. cascade-check using
        `ldoc neighbors` rather than a stale dependents.json).

        Returns [{id, label, display}], sorted by id.
        """
        all_ids = set(self._docs.keys())

        # inbound: ids that something belongs_to (i.e. have descendants)
        has_descendants: set[str] = set()
        for doc in self._docs.values():
            for target in doc.get("belongs_to", []):
                if target in all_ids:
                    has_descendants.add(target)

        results = []
        for doc_id, doc in sorted(self._docs.items()):
            has_parent = any(t in all_ids for t in doc.get("belongs_to", []))
            if not has_parent and doc_id not in has_descendants:
                results.append({
                    "id": doc_id,
                    "label": doc.get("label", ""),
                    "display": self.display_label(doc_id),
                })
        return results

    def _children_map(self) -> dict[str, list[str]]:
        """Map each doc id to the ids that `belongs_to` it (its direct children)."""
        children: dict[str, list[str]] = {}
        for doc_id, doc in self._docs.items():
            for parent in doc.get("belongs_to", []):
                if parent in self._docs:
                    children.setdefault(parent, []).append(doc_id)
        return children

    def map_overview(self) -> dict:
        """
        Return the store's navigational map: the topological ROOTS of the
        belongs_to hierarchy, ranked so an agent can orient without a cold
        search.

        A root is any doc with no resolving `belongs_to` parent. Roots split into:
          - signposts: roots that HAVE descendants (the entry points) — each
            carries its summary, transitive descendant count, effective scope,
            and its direct children (next hop, each with its own summary)
          - floating: roots with no descendants (orphans + standalone docs)

        Mirrors the viewer's structural-signpost derivation (the retired `index`
        type, re-computed from topology). Read-only.

        Returns {total, signposts: [...], floating: [...]}.
        """
        children = self._children_map()

        # Transitive descendant count, memoized, cycle-guarded.
        _desc_cache: dict[str, int] = {}

        def desc_count(doc_id: str) -> int:
            if doc_id in _desc_cache:
                return _desc_cache[doc_id]
            seen: set[str] = set()
            stack = list(children.get(doc_id, []))
            while stack:
                c = stack.pop()
                if c in seen:
                    continue
                seen.add(c)
                stack.extend(children.get(c, []))
            _desc_cache[doc_id] = len(seen)
            return len(seen)

        def _summary(doc: dict) -> str:
            s = doc.get("summary")
            return s.strip() if isinstance(s, str) else ""

        roots = [
            (doc_id, doc)
            for doc_id, doc in self._docs.items()
            if not any(p in self._docs for p in doc.get("belongs_to", []))
        ]

        signposts = []
        floating = []
        for doc_id, doc in roots:
            kids = sorted(children.get(doc_id, []))
            if kids:
                signposts.append({
                    "id": doc_id,
                    "label": doc.get("label", ""),
                    "display": self.display_label(doc_id),
                    "summary": _summary(doc),
                    "type": doc.get("type", ""),
                    "status": doc.get("status", ""),
                    "scope": self.effective_scope(doc_id),
                    "descendants": desc_count(doc_id),
                    "children": [
                        {
                            "id": c,
                            "label": self._docs[c].get("label", ""),
                            "display": self.display_label(c),
                            "summary": _summary(self._docs[c]),
                            "descendants": desc_count(c),
                        }
                        for c in sorted(kids, key=lambda c: (-desc_count(c), c))
                    ],
                })
            else:
                floating.append({
                    "id": doc_id,
                    "label": doc.get("label", ""),
                    "display": self.display_label(doc_id),
                    "summary": _summary(doc),
                    "type": doc.get("type", ""),
                    "status": doc.get("status", ""),
                })

        # Biggest signposts first; floating sorted by id for stability.
        signposts.sort(key=lambda s: (-s["descendants"], s["id"]))
        floating.sort(key=lambda f: f["id"])

        return {
            "total": len(self._docs),
            "signposts": signposts,
            "floating": floating,
        }

    def ls(self, type: str = None) -> list[dict]:
        """List all docs. Returns [{id, label, display}]."""
        results = []
        for doc_id, doc in sorted(self._docs.items()):
            if type and doc.get("type") != type:
                continue
            results.append({
                "id": doc_id,
                "label": doc.get("label", ""),
                "display": self.display_label(doc_id),
            })
        return results

    # -----------------------------------------------------------------------
    # Graph
    # -----------------------------------------------------------------------

    def neighbors(self, ref: str, kind: str = "all") -> dict:
        """
        Return neighbor edge lists for ref.

        kind: 'requires' | 'belongs_to' | 'relates' | 'provenance' |
              'superseded_by' | 'dependents' | 'provenance_of' | 'all'
        Returns dict with requested edge lists as [{id, label, display}].
        """
        doc_id = self.resolve(ref)
        doc = self._docs[doc_id]

        rev = reverse_edges(self._docs)
        ref_by = referenced_by(self._docs)

        result = {}
        if kind in ("requires", "all"):
            result["requires"] = self._edge_list(doc.get("requires", []))
        if kind in ("belongs_to", "all"):
            result["belongs_to"] = self._edge_list(doc.get("belongs_to", []))
        if kind in ("relates", "all"):
            result["relates"] = self._edge_list(doc.get("relates", []))
        if kind in ("provenance", "all"):
            result["provenance"] = self._edge_list(doc.get("provenance", []))
        if kind in ("superseded_by", "all"):
            result["superseded_by"] = self._edge_list(doc.get("superseded_by", []))
        if kind in ("dependents", "all"):
            result["dependents"] = self._edge_list(rev.get(doc_id, []))
        if kind in ("provenance_of", "all"):
            result["provenance_of"] = self._edge_list(ref_by.get(doc_id, []))

        return result

    def graph(self, ref: str, depth: int = 1, direction: str = "both") -> dict:
        """
        BFS traversal over cascade-hard edges only (requires + belongs_to).
        Navigation-only edges (relates, provenance, superseded_by) are NOT walked.

        direction: 'up' (follow requires/belongs_to), 'down' (follow dependents), 'both'
        Returns {nodes: [{id, label, display, depth}], edges: [[from_id, to_id], ...]}
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
                "label": self._docs.get(nid, {}).get("label", ""),
                "display": self.display_label(nid) if nid in self._docs else f"(missing) {nid}",
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
        label: str = "",
        summary: str = "",
        level: str = "incidental",
        status: str = "living",
        requires: list[str] = None,
        belongs_to: list[str] = None,
        relates: list[str] = None,
        provenance: list[str] = None,
        superseded_by: list[str] = None,
        tags_domain: list[str] = None,
        tags_scope: list[str] = None,
        body: str = "",
        # reference-type extras
        kind: str = "",
        source: str = "",
    ) -> str:
        """
        Create a new doc. Returns the new doc id.

        All edge arguments (requires, belongs_to, relates, provenance,
        superseded_by) accept ids, labels, or titles — resolved via resolve().
        """
        doc_id = generate_id(self.docs_dir)
        created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Resolve edge refs to ids
        edge_ids = {
            field: [self.resolve(r) for r in (refs or [])]
            for field, refs in [
                ("requires", requires),
                ("belongs_to", belongs_to),
                ("relates", relates),
                ("provenance", provenance),
                ("superseded_by", superseded_by),
            ]
        }

        # Generate label if not provided (word-boundary, never kebab)
        if not label:
            existing = (d.get("label", "") for d in self._docs.values())
            label = unique_label(title_to_label(title), existing)

        fm: dict[str, Any] = {
            "id": doc_id,
            "title": title,
            "label": label,
            "type": type,
            "status": status,
            "level": level,
            "created": created,
        }

        # Summary: scalar, omitted when empty (matches serialize emission rule)
        if summary:
            fm["summary"] = summary

        # Flat domain/scope tags: omitted entirely when empty (per schema)
        domain = list(tags_domain or [])
        scope = list(tags_scope or [])
        if domain:
            fm["domain"] = domain
        if scope:
            fm["scope"] = scope

        # Only include edge fields when non-empty (omit empty lists per spec)
        for field, ids in edge_ids.items():
            if ids:
                fm[field] = ids

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
        Update scalar frontmatter fields: title, label, summary, level, status,
        type, scope, domain.

        Resolves ref, loads doc, updates fields, writes back. Setting `summary`
        or `scope` to an empty string — or `domain` to an empty list — removes
        the field (all three are omitted on disk when empty). `scope` is a single
        STRING naming a topological zone, applying to this doc and its whole
        belongs_to subtree (see effective_scope); `domain` is a flat LIST of
        cross-cutting business/problem tags (NOT inherited).
        """
        allowed = {"title", "label", "summary", "level", "status", "type", "scope", "domain"}
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"set() does not accept fields: {unknown}. Allowed: {allowed}")

        doc_id = self.resolve(ref)
        fm, body = self._load_doc_raw(doc_id)
        for k, v in fields.items():
            if k in ("summary", "scope", "domain") and not v:
                fm.pop(k, None)
            else:
                fm[k] = v
        self._write_doc(doc_id, fm, body)

    def link(
        self,
        ref: str,
        requires: list[str] = None,
        belongs_to: list[str] = None,
        relates: list[str] = None,
        provenance: list[str] = None,
        superseded_by: list[str] = None,
    ) -> None:
        """
        Add edges. Deduplicates; does NOT remove existing edges.

        All ref args resolved via resolve().
        """
        doc_id = self.resolve(ref)
        fm, body = self._load_doc_raw(doc_id)

        for field, new_refs in [
            ("requires", requires),
            ("belongs_to", belongs_to),
            ("relates", relates),
            ("provenance", provenance),
            ("superseded_by", superseded_by),
        ]:
            if new_refs:
                existing = set(fm.get(field, []))
                for r in new_refs:
                    existing.add(self.resolve(r))
                fm[field] = sorted(existing)

        self._write_doc(doc_id, fm, body)

    def unlink(
        self,
        ref: str,
        requires: list[str] = None,
        belongs_to: list[str] = None,
        relates: list[str] = None,
        provenance: list[str] = None,
        superseded_by: list[str] = None,
    ) -> None:
        """
        Remove edges.

        All ref args resolved via resolve().
        """
        doc_id = self.resolve(ref)
        fm, body = self._load_doc_raw(doc_id)

        for field, remove_refs in [
            ("requires", requires),
            ("belongs_to", belongs_to),
            ("relates", relates),
            ("provenance", provenance),
            ("superseded_by", superseded_by),
        ]:
            if remove_refs:
                remove = {self.resolve(r) for r in remove_refs}
                remaining = [i for i in fm.get(field, []) if i not in remove]
                if remaining:
                    fm[field] = remaining
                else:
                    fm.pop(field, None)  # omit empty edge fields

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
        label: str = "",
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
            "status: reference",
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

    def set_body(self, ref: str, body: str) -> None:
        """
        Replace the body of a doc, preserving all frontmatter fields.

        This is the ONLY porcelain way to edit a doc's body content.
        """
        doc_id = self.resolve(ref)
        fm, _ = self._load_doc_raw(doc_id)
        self._write_doc(doc_id, fm, body)

    def log(
        self,
        since: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        """
        Return a READ-ONLY recent-changes view (newest first).

        Each item represents a doc that was created or had a history entry added.
        Items: {id, label, display, at, event, summary}

        `event` is 'created' or 'history'.
        `at` is the ISO 8601 timestamp of the event.
        `summary` is the history entry summary (empty for 'created' events).

        Does NOT write a review record — that is `ldoc review new`.
        """
        events: list[dict] = []

        for doc_id, doc in self._docs.items():
            created = doc.get("created", "")
            if not since or created >= since:
                events.append({
                    "id": doc_id,
                    "label": doc.get("label", ""),
                    "display": self.display_label(doc_id),
                    "at": created,
                    "event": "created",
                    "summary": "",
                })

            for h in doc.get("history", []):
                at = h.get("at", "")
                if not at:
                    continue
                if since and at < since:
                    continue
                events.append({
                    "id": doc_id,
                    "label": doc.get("label", ""),
                    "display": self.display_label(doc_id),
                    "at": at,
                    "event": "history",
                    "summary": h.get("summary", ""),
                })

        # Sort newest first
        events.sort(key=lambda e: e["at"], reverse=True)

        if limit is not None:
            events = events[:limit]

        return events

    def count(self) -> dict:
        """
        Return doc and edge count statistics.

        Returns a dict with:
          total              — total doc count
          by_type            — {type: count}
          by_level           — {level: count}
          by_status          — {status: count}
          requires_count     — total requires edge count (cascade-hard)
          belongs_to_count   — total belongs_to edge count (cascade-hard)
          relates_count      — total relates edge count (navigation)
          provenance_count   — total provenance edge count (navigation)
          superseded_by_count— total superseded_by edge count
        """
        by_type: dict[str, int] = {}
        by_level: dict[str, int] = {}
        by_status: dict[str, int] = {}
        requires_count = 0
        belongs_to_count = 0
        relates_count = 0
        provenance_count = 0
        superseded_by_count = 0

        for doc in self._docs.values():
            t = doc.get("type") or "(none)"
            by_type[t] = by_type.get(t, 0) + 1

            lv = doc.get("level") or "(none)"
            by_level[lv] = by_level.get(lv, 0) + 1

            ss = doc.get("status") or "(none)"
            by_status[ss] = by_status.get(ss, 0) + 1

            requires_count += len(doc.get("requires", []))
            belongs_to_count += len(doc.get("belongs_to", []))
            relates_count += len(doc.get("relates", []))
            provenance_count += len(doc.get("provenance", []))
            superseded_by_count += len(doc.get("superseded_by", []))

        return {
            "total": len(self._docs),
            "by_type": dict(sorted(by_type.items())),
            "by_level": dict(sorted(by_level.items())),
            "by_status": dict(sorted(by_status.items())),
            "requires_count": requires_count,
            "belongs_to_count": belongs_to_count,
            "relates_count": relates_count,
            "provenance_count": provenance_count,
            "superseded_by_count": superseded_by_count,
        }

    def validate_edge_refs(
        self,
        requires: list[str] = None,
        belongs_to: list[str] = None,
        relates: list[str] = None,
        provenance: list[str] = None,
        superseded_by: list[str] = None,
    ) -> list[str]:
        """
        Validate that all edge refs resolve. Returns a list of unresolved ref strings.
        Does NOT raise — callers check the returned list.
        """
        unresolved = []
        all_refs = list(requires or []) + list(belongs_to or []) + \
                   list(relates or []) + list(provenance or []) + \
                   list(superseded_by or [])
        for r in all_refs:
            try:
                self.resolve(r)
            except ValueError:
                unresolved.append(r)
        return unresolved

    def delete(self, doc_id: str) -> None:
        """Delete a doc by id. Use only for throwaway/test docs."""
        path = self.docs_dir / f"{doc_id}.md"
        if path.exists():
            path.unlink()
        self._reload()
