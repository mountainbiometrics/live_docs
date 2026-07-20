"""
livedocs — Shared library for the live_docs tooling.

Stdlib only (pathlib, re, datetime). No external dependencies. Import from other scripts:

    from livedocs import DOCS_DIR, RAW_DIR, REVIEWS_DIR, parse_doc, load_all, forward_edges, reverse_edges, id_title_map, generate_id, KB

Store location: resolved by discovery, not by where this code lives. `ldoc` walks
up from the current working directory for a `.live_docs.toml` marker, falling back
to ~/.config/live_docs/config.toml. See model.py for the resolution rules.

Exports are lazy so submodules like user_config can load without locating a store.
"""

from __future__ import annotations

import importlib

_EXPORT_MAP = [
    ("model",     {"STORE_ROOT", "CONSUMER_ROOT", "REPO_ROOT", "DOCS_DIR", "RAW_DIR", "REVIEWS_DIR", "SESSIONS_DIR",
                   "LEXICON_DIR", "INBOX_DIR", "INDEX_DIR",
                   "VALID_TYPES", "VALID_STATUSES", "VALID_LEVELS", "VALID_REFERENCE_KINDS",
                   "is_archived", "ARCHIVED_IMMUTABLE_MSG",
                   "generate_id", "generate_session_id", "session_start_iso",
                   "change_types_for_fields", "dominant_change_type",
                   "title_to_label", "unique_label", "display_label",
                   "ref_token", "render_ref_token", "WIKILINK_RE", "doc_prefix"}),
    ("serialize", {"CANONICAL_FIELD_ORDER", "REFERENCE_EXTRA_FIELDS", "EDGE_FIELDS",
                   "parse_doc", "dump_doc", "build_raw_frontmatter"}),
    ("sessions",  {"SessionStore", "record_doc_change", "resolve_open_session",
                   "ensure_session"}),
    ("lexicon",   {"LexiconStore", "parse_term", "dump_term", "term_id", "display_form",
                   "ref_to_id", "iter_term_links", "compute_term_stats", "TERM_LINK_RE"}),
    ("graph",     {"forward_edges", "reverse_edges", "reverse_requires", "reverse_belongs_to",
                   "dangling_edges", "inbound_edges",
                   "reference_edges", "referenced_by", "dangling_references", "relates_edges",
                   "superseded_by_edges", "id_title_map", "BLOCKING_EDGE_FIELDS", "ALL_EDGE_FIELDS"}),
    ("lint",      {"body_doc_refs", "edged_ids", "prose_links_not_edged",
                   "malformed_body_wikilinks", "BODY_WIKILINK_RE"}),
    ("kb",        {"KB", "load_all"}),
    ("reviews",   {"ReviewLedger", "parse_review", "dump_review", "strip_wal_archive"}),
    ("viewer",    {"build_viewer", "auto_rebuild_viewer", "auto_viewer_enabled"}),
]

# Derived from _EXPORT_MAP — single source of truth.
__all__ = sorted(name for _, names in _EXPORT_MAP for name in names)

# Reverse lookup: name → module string (built once at import time).
_NAME_TO_MODULE: dict[str, str] = {
    name: mod for mod, names in _EXPORT_MAP for name in names
}


def __getattr__(name: str):
    mod_name = _NAME_TO_MODULE.get(name)
    if mod_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    mod = importlib.import_module(f".{mod_name}", __name__)
    obj = getattr(mod, name)
    # Cache on the package so subsequent accesses skip __getattr__ entirely.
    globals()[name] = obj
    return obj
