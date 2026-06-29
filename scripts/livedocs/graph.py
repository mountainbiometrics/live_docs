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

# Outbound edge fields whose broken refs are blocking errors in validate / edges.
BLOCKING_EDGE_FIELDS = ("requires", "belongs_to", "relates", "superseded_by")

# All five edge fields — includes provenance (warning-only when dangling).
ALL_EDGE_FIELDS = BLOCKING_EDGE_FIELDS + ("provenance",)


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
    Used by graph BFS (cascade needs the union); for display see
    reverse_requires / reverse_belongs_to.
    """
    all_ids = set(docs.keys())
    rev: dict = {doc_id: [] for doc_id in all_ids}
    for doc_id, doc in docs.items():
        for target_id in _hard_edge_ids(doc):
            if target_id in rev:
                rev[target_id].append(doc_id)
    return rev


def _reverse_field(docs: dict, field: str) -> dict:
    """Return {id: [ids whose `field` list contains this id]}."""
    all_ids = set(docs.keys())
    rev: dict = {doc_id: [] for doc_id in all_ids}
    for doc_id, doc in docs.items():
        for target_id in doc.get(field, []):
            if target_id in rev:
                rev[target_id].append(doc_id)
    return rev


def reverse_requires(docs: dict) -> dict:
    """
    Build reverse requires map: {id: [ids whose `requires` lists this id]}.

    "required_by" — docs that depend on the target.
    """
    return _reverse_field(docs, "requires")


def reverse_belongs_to(docs: dict) -> dict:
    """
    Build reverse belongs_to map: {id: [ids whose `belongs_to` lists this id]}.

    "children" — docs that are structural members of the target (parent).
    """
    return _reverse_field(docs, "belongs_to")


def dangling_edges(docs: dict) -> list:
    """
    Return list of (from_id, target_id, edge_field) tuples where target_id
    does not exist in docs.

    Covers all blocking edge types: requires, belongs_to, relates, superseded_by.
    Shared by ldoc edges and validate.
    """
    all_ids = set(docs.keys())
    dangling = []
    for doc_id, doc in docs.items():
        for field in BLOCKING_EDGE_FIELDS:
            for target_id in doc.get(field, []):
                if target_id and target_id not in all_ids:
                    dangling.append((doc_id, target_id, field))
    return dangling


def inbound_edges(docs: dict, target_id: str) -> list[tuple[str, str]]:
    """
    Return sorted unique (referrer_id, edge_field) for every inbound ref to target_id.

    Covers requires, belongs_to, relates, provenance (in-graph doc ids only),
    and superseded_by.
    """
    if target_id not in docs:
        return []

    inbound: set[tuple[str, str]] = set()

    for referrer_id, doc in docs.items():
        for field in ALL_EDGE_FIELDS:
            if target_id in doc.get(field, []):
                inbound.add((referrer_id, field))

    return sorted(inbound)


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
    return _reverse_field(docs, "provenance")


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
