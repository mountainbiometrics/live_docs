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
    DOCS_DIR, RAW_DIR, LABEL_RE,
    generate_id, title_to_label, unique_label, display_label,
)
from .serialize import parse_doc, dump_doc, _yaml_str
from .graph import reverse_edges, referenced_by, forward_edges


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

        depends_on, references, dependents, referenced_by each rendered as
        [{id, label, display}] rather than bare id lists.
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
            "depends_on": self._edge_list(doc.get("depends_on", [])),
            "references": self._edge_list(doc.get("references", [])),
            "dependents": self._edge_list(rev.get(doc_id, [])),
            "referenced_by": self._edge_list(ref_by.get(doc_id, [])),
        }

    def find(
        self,
        query: str | None = None,
        type: str | None = None,
        level: str | None = None,
        state: str | None = None,
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
            if state and doc.get("state") != state:
                continue
            if status and doc.get("status") != status:
                continue

            tags = doc.get("tags", {})
            if scope and scope not in tags.get("scope", []):
                continue
            if domain and domain not in tags.get("domain", []):
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

        kind: 'depends_on' | 'references' | 'dependents' | 'referenced_by' | 'all'
        Returns dict with requested edge lists as [{id, label, display}].
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

        depends_on and references accept ids, labels, or titles — resolved via resolve().
        """
        doc_id = generate_id(self.docs_dir)
        created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Resolve edge refs to ids
        dep_ids = [self.resolve(r) for r in (depends_on or [])]
        ref_ids = [self.resolve(r) for r in (references or [])]

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
        Update scalar frontmatter fields: title, label, level, state, status, type.

        Resolves ref, loads doc, updates fields, writes back.
        """
        allowed = {"title", "label", "level", "state", "status", "type"}
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
          by_state           — {state: count}
          by_status          — {status: count}
          edge_count         — total depends_on edge count
          reference_count    — total references edge count
        """
        by_type: dict[str, int] = {}
        by_level: dict[str, int] = {}
        by_state: dict[str, int] = {}
        by_status: dict[str, int] = {}
        edge_count = 0
        reference_count = 0

        for doc in self._docs.values():
            t = doc.get("type") or "(none)"
            by_type[t] = by_type.get(t, 0) + 1

            lv = doc.get("level") or "(none)"
            by_level[lv] = by_level.get(lv, 0) + 1

            st = doc.get("state") or "(none)"
            by_state[st] = by_state.get(st, 0) + 1

            ss = doc.get("status") or "(none)"
            by_status[ss] = by_status.get(ss, 0) + 1

            edge_count += len(doc.get("depends_on", []))
            reference_count += len(doc.get("references", []))

        return {
            "total": len(self._docs),
            "by_type": dict(sorted(by_type.items())),
            "by_level": dict(sorted(by_level.items())),
            "by_state": dict(sorted(by_state.items())),
            "by_status": dict(sorted(by_status.items())),
            "edge_count": edge_count,
            "reference_count": reference_count,
        }

    def validate_edge_refs(
        self,
        depends_on: list[str],
        references: list[str],
    ) -> list[str]:
        """
        Validate that all edge refs resolve. Returns a list of unresolved ref strings.
        Does NOT raise — callers check the returned list.
        """
        unresolved = []
        for r in depends_on:
            try:
                self.resolve(r)
            except ValueError:
                unresolved.append(r)
        for r in references:
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
