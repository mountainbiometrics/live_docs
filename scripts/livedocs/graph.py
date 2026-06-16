"""
graph.py — Pure edge-map functions over a docs dict.

All functions are read-only and operate on an already-loaded docs dict.
Stdlib only. No external dependencies.
"""


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


def id_title_map(docs: dict) -> dict:
    """Return {id: title} for all docs."""
    return {doc_id: doc.get("title", doc_id) for doc_id, doc in docs.items()}
