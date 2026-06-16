"""
kb.py — KB class and load_all: unified store API for live_docs.

KB wraps parse, serialize, graph, and model helpers into a single query/mutation
layer. Mutators are DUMB: they write what you tell them; no cascade judgment here.
Stdlib only. No external dependencies.
"""

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
        query: str = None,
        type: str = None,
        level: str = None,
        state: str = None,
        status: str = None,
        scope: str = None,
        domain: str = None,
    ) -> list[dict]:
        """
        Search docs with optional filters. Returns [{id, label, display, snippet}].

        query matches title + label + body (case-insensitive).
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
                label = doc.get("label", "").lower()
                body = doc.get("body", "").lower()
                if q in title or q in label or q in body:
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

    def delete(self, doc_id: str) -> None:
        """Delete a doc by id. Use only for throwaway/test docs."""
        path = self.docs_dir / f"{doc_id}.md"
        if path.exists():
            path.unlink()
        self._reload()
