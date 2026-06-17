"""
livedocs — Shared library for the live_docs tooling.

Stdlib only (pathlib, re, datetime). No external dependencies. Import from other scripts:

    from livedocs import DOCS_DIR, RAW_DIR, parse_doc, load_all, forward_edges, reverse_edges, id_title_map, generate_id, KB

Repo-root detection: the repo root is the parent of the parent of the directory that
contains this package (scripts/livedocs/ → scripts/ → repo root).
"""

from .model import (
    REPO_ROOT,
    DOCS_DIR,
    RAW_DIR,
    TEMPLATES_DIR,
    REVIEWS_DIR,
    VALID_TYPES,
    VALID_STATUSES,
    VALID_LEVELS,
    VALID_REFERENCE_KINDS,
    LABEL_RE,
    generate_id,
    title_to_label,
    unique_label,
    display_label,
    ref_token,
    render_ref_token,
    WIKILINK_RE,
    doc_prefix,
)

from .serialize import (
    CANONICAL_FIELD_ORDER,
    REFERENCE_EXTRA_FIELDS,
    EDGE_FIELDS,
    parse_doc,
    dump_doc,
)

from .graph import (
    forward_edges,
    reverse_edges,
    dangling_edges,
    reference_edges,
    referenced_by,
    dangling_references,
    relates_edges,
    superseded_by_edges,
    id_title_map,
)

from .kb import (
    KB,
    load_all,
    # KB.set_body, KB.log, KB.count, KB.validate_edge_refs are methods on KB
)

from .reviews import (
    ReviewLedger,
    parse_review,
    dump_review,
)

__all__ = [
    # model
    "REPO_ROOT",
    "DOCS_DIR",
    "RAW_DIR",
    "TEMPLATES_DIR",
    "REVIEWS_DIR",
    "VALID_TYPES",
    "VALID_STATUSES",
    "VALID_LEVELS",
    "VALID_REFERENCE_KINDS",
    "LABEL_RE",
    "generate_id",
    "title_to_label",
    "unique_label",
    "display_label",
    "ref_token",
    "render_ref_token",
    "WIKILINK_RE",
    "doc_prefix",
    # serialize
    "CANONICAL_FIELD_ORDER",
    "REFERENCE_EXTRA_FIELDS",
    "EDGE_FIELDS",
    "parse_doc",
    "dump_doc",
    # graph
    "forward_edges",
    "reverse_edges",
    "dangling_edges",
    "reference_edges",
    "referenced_by",
    "dangling_references",
    "relates_edges",
    "superseded_by_edges",
    "id_title_map",
    # kb
    "KB",
    "load_all",
    # reviews
    "ReviewLedger",
    "parse_review",
    "dump_review",
]
