"""
lint.py — Read-only body wikilink lint helpers for validate / edges.

Stdlib only. No external dependencies.
"""

import re

# Canonical body refs: bare [[id]] or ![[id]]; pipe form is tolerated for extraction
# but flagged separately as malformed.
BODY_WIKILINK_RE = re.compile(r"!?\[\[(\d{14})(?:\|[^\]]*)?\]\]")

MALFORMED_PIPE_WIKILINK_RE = re.compile(r"!\[\[(\d{14})\|[^\]]+\]\]|\[\[(\d{14})\|[^\]]+\]\]")

MALFORMED_PAREN_AFTER_WIKILINK_RE = re.compile(r"\[\[(\d{14})\]\]\s+\([^)]+\)")

EDGE_FIELDS = ("requires", "belongs_to", "relates", "provenance", "superseded_by")


def body_doc_refs(body: str) -> set[str]:
    """Return doc ids referenced by [[id]] / ![[id]] tokens in body prose."""
    return set(BODY_WIKILINK_RE.findall(body or ""))


def edged_ids(doc: dict) -> set[str]:
    """Return all ids listed in any edge field on the doc."""
    ids: set[str] = set()
    for field in EDGE_FIELDS:
        for item in doc.get(field, []) or []:
            if item:
                ids.add(item)
    return ids


def prose_links_not_edged(doc: dict) -> set[str]:
    """Body wikilink ids absent from every edge field on the same doc."""
    return body_doc_refs(doc.get("body", "")) - edged_ids(doc)


def malformed_body_wikilinks(body: str) -> list[tuple[str, str]]:
    """
    Return [(kind, matched_text), ...] for non-canonical body wikilink syntax.

    kind is 'pipe' or 'paren'.
    """
    text = body or ""
    found: list[tuple[str, str]] = []
    seen: set[str] = set()

    for pattern, kind in [
        (MALFORMED_PIPE_WIKILINK_RE, "pipe"),
        (MALFORMED_PAREN_AFTER_WIKILINK_RE, "paren"),
    ]:
        for m in pattern.finditer(text):
            token = m.group(0)
            if token not in seen:
                seen.add(token)
                found.append((kind, token))

    return found
