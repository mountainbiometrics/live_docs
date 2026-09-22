"""
model.py — the doc model: what a live_docs doc is made of.

Enum sets, the archived test, the change-type taxonomy, id generation, and the
label and wiki-link rendering every surface shares. Where a store lives and how
it is opened is store.py's; nothing here reads a config or touches a path.

Stdlib only. No external dependencies.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


# ---------------------------------------------------------------------------
# Valid enum values
# ---------------------------------------------------------------------------

VALID_TYPES = {
    "type", "principle", "goal", "decision", "constraint",
    "requirement", "use-case", "guide", "component", "reference",
}
VALID_STATUSES = {"living", "target", "deprecated", "reference"}
VALID_LEVELS = {"incidental", "trial", "preference", "requirement"}
VALID_REFERENCE_KINDS = {"brainstorm", "plan", "clipping", "external"}

# The same three enums as annotations, so a method that takes one says which
# values it takes and a surface reading its signature can offer them.
DocType = Literal[tuple(sorted(VALID_TYPES))]
DocStatus = Literal[tuple(sorted(VALID_STATUSES))]
DocLevel = Literal[tuple(sorted(VALID_LEVELS))]


def is_archived(doc: dict | None) -> bool:
    """True when a doc is reference/archived surface material.

    Matches viewer ``isArchived``: ``type: reference`` OR ``status: reference``.
    ``status: target`` is NOT archived — demotion is about reference material,
    not the living-vs-target adoption axis.
    """
    if not doc:
        return False
    return doc.get("type") == "reference" or doc.get("status") == "reference"


# Clear message when porcelain refuses to mutate a reference snapshot.
ARCHIVED_IMMUTABLE_MSG = (
    "refusing to mutate reference/archived doc {ref!r} "
    "(type:reference or status:reference) — snapshots are immutable; "
    "delete and re-ingest if the snapshot is wrong"
)


# ---------------------------------------------------------------------------
# Change-type taxonomy (change-type-taxonomy 20260701201617)
# ---------------------------------------------------------------------------
#
# Every mutation carries a change_type set by WHICH command/field produced it,
# not inferred later. A command may touch several categories; the WAL records
# the full LIST. When rolled into a review, each doc is filed ONCE under a
# single dominant type by the precedence below.

VALID_CHANGE_TYPES = ("addition", "revision", "restructure", "organizational", "deletion")

# Field/command → change_type slotting. `new` is addition; `rm` is deletion;
# a scalar/edge field maps to its category. Keys are the field names the
# mutating commands touch (plus the pseudo-commands 'new' / 'rm').
FIELD_CHANGE_TYPE = {
    # addition
    "new": "addition",
    # revision — content actually changed
    "body": "revision",
    "label": "revision",
    "title": "revision",
    "summary": "revision",
    # restructure — a harder form of reorganization
    "requires": "restructure",
    "belongs_to": "restructure",
    "status": "restructure",
    "level": "restructure",
    "type": "restructure",
    "scope": "restructure",
    "superseded_by": "restructure",
    # organizational — soft edges and tags
    "relates": "organizational",
    "provenance": "organizational",
    "domain": "organizational",
    # deletion
    "rm": "deletion",
}

# Review-filing precedence: the dominant type when a doc's change list spans
# several categories. deletion > addition > revision > restructure > organizational.
# A doc created in the session is filed as an Addition even if it was also edited
# while being created; deletion still trumps (created-then-deleted is a Deletion).
CHANGE_TYPE_PRECEDENCE = ["deletion", "addition", "revision", "restructure", "organizational"]


def change_types_for_fields(fields) -> list[str]:
    """Map an iterable of touched field/command names to the DISTINCT list of
    change_types they belong to, in canonical taxonomy order.

    Unknown fields are ignored. Returns [] when nothing maps.
    """
    seen: set[str] = set()
    for f in fields or []:
        ct = FIELD_CHANGE_TYPE.get(f)
        if ct:
            seen.add(ct)
    return [ct for ct in VALID_CHANGE_TYPES if ct in seen]


def dominant_change_type(change_types) -> str:
    """Return the single dominant change_type for review-filing, by precedence
    deletion > addition > revision > restructure > organizational.

    Accepts a list (the WAL's change_type list) or a single string. Returns ''
    when nothing recognizable is present (legacy entries carry no change_type).
    """
    if isinstance(change_types, str):
        cts = {change_types}
    else:
        cts = set(change_types or [])
    for ct in CHANGE_TYPE_PRECEDENCE:
        if ct in cts:
            return ct
    return ""


# ---------------------------------------------------------------------------
# Collision-safe ID generation (shared by ldoc new and ingest_raw.py)
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


def generate_session_id() -> str:
    """Return a sortable, collision-resistant session id: ``<YYYYMMDDHHMMSS>-<hex>``.

    The 14-digit timestamp prefix keeps sessions naturally ordered and lets
    review generation recover the session's start time (see session_start_iso);
    the random suffix avoids collisions between sessions minted in the same
    second, including concurrent agents. Unlike generate_id there is no
    directory to disambiguate against — the suffix carries the entropy.
    """
    base = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{base}-{os.urandom(2).hex()}"


def session_start_iso(session_id: str) -> str:
    """Recover the ISO 8601 UTC start time embedded in a session id's prefix.

    Returns '' when the id carries no parseable 14-digit timestamp prefix.
    Used to classify Additions (docs created during the session), since a
    freshly-created doc has no history entry to stamp (history-is-changes).
    """
    m = re.match(r"(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", session_id or "")
    if not m:
        return ""
    y, mo, d, h, mi, s = m.groups()
    return f"{y}-{mo}-{d}T{h}:{mi}:{s}Z"


# ---------------------------------------------------------------------------
# Label generation utilities
# ---------------------------------------------------------------------------

def title_to_label(title: str) -> str:
    """
    Derive a label from a title by taking whole words up to ~24 chars.

    Rules:
    - Break on word boundaries — never truncate mid-word.
    - Accumulate whole words while the running length stays within ~24 chars.
      Always keep at least the first word, even if it alone exceeds the budget.
    - The result is Title Case (each word capitalised); whitespace between words
      is preserved; NOT kebab-cased.
    - Strip trailing punctuation from each word before capitalising.

    Per label-and-title decision: labels are Title-Case names, not kebab slugs.
    """
    MAX_LEN = 24
    words = title.split()
    if not words:
        return ""

    # Strip trailing punctuation from each raw word before building
    stripped = [re.sub(r'[^A-Za-z0-9]+$', '', w) for w in words]
    stripped = [w for w in stripped if w]  # drop words that were pure punctuation

    if not stripped:
        return ""

    chosen: list[str] = [stripped[0]]
    length = len(stripped[0])
    for w in stripped[1:]:
        # +1 accounts for the joining space
        if length + 1 + len(w) > MAX_LEN:
            break
        chosen.append(w)
        length += 1 + len(w)

    # Title Case (each word capitalised, whitespace preserved)
    label = " ".join(w.capitalize() for w in chosen)
    return label


def unique_label(base: str, existing_labels) -> str:
    """
    Return base label, appending ' 2', ' 3', etc. until unique.

    `existing_labels` is any iterable of labels; uniqueness is case-insensitive.
    """
    existing_lower = {e.lower() for e in existing_labels}
    label = base
    n = 2
    while label.lower() in existing_lower:
        label = f"{base} {n}"
        n += 1
    return label


# ---------------------------------------------------------------------------
# Human-readable rendering — single source of truth for the dict-based tools.
# Human output must always carry the label so a line is never a bare id.
# ---------------------------------------------------------------------------

def display_label(doc: dict) -> str:
    """Return the '<Type>: <Title>' display string for a doc dict."""
    t = doc.get("type", "?")
    title = doc.get("title", doc.get("id", "?"))
    return f"{t.capitalize()}: {title}"



# A stored reference is a bare wiki-link to a doc id: [[20260616181719]].
# The 14-digit guard keeps a stray timestamp in prose from being mistaken
# for a ref, and an optional |alias is tolerated so render output round-trips.
WIKILINK_RE = re.compile(r'\[\[(\d{14})(?:\|[^\]]*)?\]\]')


def ref_token(doc_or_id) -> str:
    """
    Canonical *stored* reference: '[[<id>]]'.

    This is what gets serialized into review summaries and any other artifact.
    It carries only the id — the single source of truth — so a label change
    never leaves a stale copy behind. Accepts a doc dict or a bare id string.
    """
    doc_id = doc_or_id.get("id", "?") if isinstance(doc_or_id, dict) else str(doc_or_id)
    return f"[[{doc_id}]]"


def render_ref_token(doc_id: str, doc: dict | None) -> str:
    """
    Render a stored '[[<id>]]' for human display as '[[<id>|<Type>: <Title>]]'.

    The label is resolved live from the current doc, so display always reflects
    the doc's present title. A missing target renders explicitly rather than
    silently dropping the ref. The |alias form is also what Obsidian shows.
    """
    if doc is None:
        return f"[[{doc_id}|(missing)]]"
    return f"[[{doc_id}|{display_label(doc)}]]"


def doc_prefix(doc: dict) -> str:
    """Return the '<id> [<label>] "<Type>: <Title>"' human prefix for a doc dict."""
    doc_id = doc.get("id", "<unknown>")
    label = doc.get("label", "") or "(no label)"
    return f'{doc_id} [{label}] "{display_label(doc)}"'
