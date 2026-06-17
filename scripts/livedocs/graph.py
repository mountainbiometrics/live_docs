"""
graph.py — Pure edge-map functions over a docs dict.

All functions are read-only and operate on an already-loaded docs dict.
Stdlib only. No external dependencies.

Edge semantics (per schema spec 2026-06-17):
  requires      — hard edge: cascades in both directions
  belongs_to    — hard edge: cascades in both directions (structural hierarchy)
  relates       — navigation/clustering only; no cascade
  provenance    — navigation only; no cascade; may target docs outside graph
  superseded_by — deprecation pointer; triggers cascade on reverse requires/belongs_to

forward_edges / reverse_edges cover ONLY cascade-hard edges (requires + belongs_to).
relate_edges / provenance_edges are navigation-only and must NEVER drive cascade.
"""


def _hard_edge_ids(doc: dict) -> list:
    """Return all ids in cascade-hard edge fields (requires + belongs_to)."""
    ids = []
    ids.extend(doc.get("requires", []))
    ids.extend(doc.get("belongs_to", []))
    return ids


def forward_edges(docs: dict) -> dict:
    """
    Build forward edge map: {id: [ids this doc has hard edges to]}.

    Covers requires + belongs_to (both are cascade-hard).
    Only includes edges where the target id exists in docs (no dangling).
    """
    all_ids = set(docs.keys())
    fwd = {}
    for doc_id, doc in docs.items():
        targets = [d for d in _hard_edge_ids(doc) if d in all_ids]
        fwd[doc_id] = targets
    return fwd


def reverse_edges(docs: dict) -> dict:
    """
    Build reverse edge map: {id: [ids that have a hard edge pointing HERE]}.

    Covers requires + belongs_to.  Derived from forward_edges; never stored.
    """
    all_ids = set(docs.keys())
    rev: dict = {doc_id: [] for doc_id in all_ids}
    for doc_id, doc in docs.items():
        for target_id in _hard_edge_ids(doc):
            if target_id in rev:
                rev[target_id].append(doc_id)
    return rev


def dangling_edges(docs: dict) -> list:
    """
    Return list of (from_id, target_id, edge_field) tuples where target_id
    does not exist in docs.

    Covers cascade-hard edges (requires + belongs_to).
    """
    all_ids = set(docs.keys())
    dangling = []
    for doc_id, doc in docs.items():
        for field in ("requires", "belongs_to"):
            for target_id in doc.get(field, []):
                if target_id not in all_ids:
                    dangling.append((doc_id, target_id, field))
    return dangling


# ---------------------------------------------------------------------------
# Provenance (ex-references) graph helpers — navigation ONLY, never cascade
# ---------------------------------------------------------------------------

def reference_edges(docs: dict) -> dict:
    """
    Build forward provenance map: {id: [ids this doc lists in provenance]}.

    NAVIGATION ARTIFACT — immutable derivation lineage.
    MUST NEVER be used as cascade input; use forward_edges for that.
    Only includes entries where the referenced id exists in docs (no dangling).

    Note: provenance may also target docs outside the graph (raw/, URLs) —
    those are simply absent from the returned lists here.
    """
    all_ids = set(docs.keys())
    fwd = {}
    for doc_id, doc in docs.items():
        refs = [r for r in doc.get("provenance", []) if r in all_ids]
        fwd[doc_id] = refs
    return fwd


def referenced_by(docs: dict) -> dict:
    """
    Build reverse provenance map: {id: [ids that list this id in provenance]}.

    NAVIGATION ARTIFACT — reverse provenance / "derived from" lookup.
    MUST NEVER be used as cascade input; use reverse_edges for that.
    """
    all_ids = set(docs.keys())
    rev: dict = {doc_id: [] for doc_id in all_ids}
    for doc_id, doc in docs.items():
        for ref_id in doc.get("provenance", []):
            if ref_id in rev:
                rev[ref_id].append(doc_id)
    return rev


def dangling_references(docs: dict) -> list:
    """
    Return list of (from_id, ref_id) tuples where ref_id does not exist in docs.

    Covers provenance field only (use dangling_edges for cascade-hard edges).
    Note: provenance may intentionally target raw/ docs not in docs/; those
    are reported here but are expected and non-blocking in validate.
    """
    all_ids = set(docs.keys())
    dangling = []
    for doc_id, doc in docs.items():
        for ref_id in doc.get("provenance", []):
            if ref_id not in all_ids:
                dangling.append((doc_id, ref_id))
    return dangling


# ---------------------------------------------------------------------------
# relates / superseded_by navigation helpers
# ---------------------------------------------------------------------------

def relates_edges(docs: dict) -> dict:
    """
    Build forward relates map: {id: [ids this doc relates to]}.

    NAVIGATION ONLY — symmetric clustering/kinship. No cascade.
    Only includes entries where the target id exists in docs.
    """
    all_ids = set(docs.keys())
    fwd = {}
    for doc_id, doc in docs.items():
        rel = [r for r in doc.get("relates", []) if r in all_ids]
        fwd[doc_id] = rel
    return fwd


def superseded_by_edges(docs: dict) -> dict:
    """
    Build forward superseded_by map: {id: [replacement doc ids]}.

    Used only for display/navigation; cascade is triggered via reverse
    requires/belongs_to when a doc becomes deprecated, not here.
    Only includes entries where the target id exists in docs.
    """
    all_ids = set(docs.keys())
    fwd = {}
    for doc_id, doc in docs.items():
        sup = [r for r in doc.get("superseded_by", []) if r in all_ids]
        fwd[doc_id] = sup
    return fwd


def id_title_map(docs: dict) -> dict:
    """Return {id: title} for all docs."""
    return {doc_id: doc.get("title", doc_id) for doc_id, doc in docs.items()}
