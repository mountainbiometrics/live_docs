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
from dataclasses import dataclass
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
# Lifecycle only. Deferral is `realization: deferred`; a current path coexisting
# with its planned successor is `superseded_by` on the still-living doc.
VALID_STATUSES = {"living", "deprecated", "reference"}
# Read-only: still parsed so existing docs keep working, but validate warns and
# nothing writes it. (`target` split into living + a realization.)
RETIRED_STATUSES = {"target"}
VALID_REFERENCE_KINDS = {"brainstorm", "plan", "clipping", "external"}

# The four facets that replaced `level`; each answers one question.
# intent: what the person did to make the claim exist. force: how hard it binds.
# realization: whether the claimed thing exists in the implementation.
# imposed_by: what makes the claim hold.
VALID_INTENTS = {"requested", "chosen", "incidental"}
VALID_FORCES = {"must", "should", "may"}
VALID_REALIZATIONS = {"realized", "partial", "planned", "deferred", "unassessed"}
VALID_IMPOSITIONS = {"environment", "tradeoff", "choice"}

# The same enums as annotations, so a method that takes one says which values it
# takes and a surface reading its signature can offer them.
DocType = Literal[tuple(sorted(VALID_TYPES))]
DocStatus = Literal[tuple(sorted(VALID_STATUSES))]
DocIntent = Literal[tuple(sorted(VALID_INTENTS))]
DocForce = Literal[tuple(sorted(VALID_FORCES))]
DocRealization = Literal[tuple(sorted(VALID_REALIZATIONS))]
DocImposition = Literal[tuple(sorted(VALID_IMPOSITIONS))]


# ---------------------------------------------------------------------------
# What each doc type decides about the facets
# ---------------------------------------------------------------------------

Presence = Literal["required", "optional", "forbidden"]


@dataclass(frozen=True)
class TypeSpec:
    """Which facets a doc type carries, and the why-chain it should sit in.

    ``required`` is an error when the tool writes the doc and a warning on an
    existing one (loose on input, strict on output); ``forbidden`` is an error
    either way. ``realization_verb`` is the predicate for what realization means
    on this type ("is reached", "exists"); a message uses it to ask the
    question in the type's own terms.
    ``expected_requires`` are the types a doc of this type should depend on, any
    one of which satisfies it; the chain reads goal/use-case, then norm, then
    decision/component.
    """

    intent: Presence = "required"
    force: Presence = "forbidden"
    realization: Presence = "forbidden"
    realization_verb: str = ""
    imposed_by: Presence = "optional"
    expected_requires: tuple = ()


# The one copy of the per-type rules. Everything that writes or checks a doc
# reads this; nothing restates it. `type` is the meta-type that defines types and
# carries no facets beyond intent.
TYPE_TABLE: dict[str, TypeSpec] = {
    "goal": TypeSpec(realization="required", realization_verb="is reached"),
    "use-case": TypeSpec(realization="required", realization_verb="is supported",
                         expected_requires=("goal",)),
    "principle": TypeSpec(force="required",
                          expected_requires=("goal", "use-case")),
    # What an imposed_by value expects upstream (TRADEOFF_UPSTREAM,
    # CHOICE_UPSTREAM) is checked off imposed_by itself, since it applies to any
    # type that carries it. A constraint admits every value: `environment` for an
    # external one, `tradeoff` for a technical one, `choice` for an organizational
    # one.
    "constraint": TypeSpec(force="required", imposed_by="required"),
    "requirement": TypeSpec(force="required", realization="required",
                            realization_verb="is met",
                            expected_requires=("goal", "use-case")),
    "decision": TypeSpec(force="required", realization="required",
                         realization_verb="is in effect",
                         expected_requires=("principle", "constraint", "requirement")),
    "component": TypeSpec(realization="required", realization_verb="exists",
                          expected_requires=("decision", "requirement")),
    "guide": TypeSpec(force="required", expected_requires=("principle", "decision")),
    "reference": TypeSpec(intent="forbidden", imposed_by="forbidden"),
    "type": TypeSpec(),
}

# A claim imposed by `tradeoff` follows from a choice recorded elsewhere, so it
# must depend on the decision or component that made the choice.
TRADEOFF_UPSTREAM = ("decision", "component")

# A claim imposed by `choice` is set directly, so it should depend on the goal,
# use-case, or principle that motivates it.
CHOICE_UPSTREAM = ("goal", "use-case", "principle")

# Every frontmatter field a facet owns. `realization_refs` and
# `realization_verified` ride with `realization`; `intent_basis` rides with
# `intent`.
FACET_FIELDS = (
    "intent", "intent_basis", "force", "realization",
    "realization_refs", "realization_verified", "imposed_by",
)
_COMPANIONS = {
    "intent_basis": "intent",
    "realization_refs": "realization",
    "realization_verified": "realization",
}


def facet_forbidden(doc_type: str, field: str) -> bool:
    """True when this type's table entry forbids `field` (or its owning facet)."""
    spec = TYPE_TABLE.get(doc_type)
    if spec is None:
        return False
    return getattr(spec, _COMPANIONS.get(field, field)) == "forbidden"


def facet_required(doc_type: str, field: str) -> bool:
    """True when this type's table entry requires `field`.

    Companions are never required: a basis is required by the intent *value*
    (see ``intent_needs_basis``), not by the type.
    """
    spec = TYPE_TABLE.get(doc_type)
    return spec is not None and field not in _COMPANIONS \
        and getattr(spec, field) == "required"


def intent_needs_basis(intent: str | None) -> bool:
    """`requested` and `chosen` are claims about the person; the basis is the evidence."""
    return intent in ("requested", "chosen")


def is_archived(doc: dict | None) -> bool:
    """True when a doc is reference/archived surface material.

    Matches viewer ``isArchived``: ``type: reference`` OR ``status: reference``.
    Lifecycle (`deprecated`) is not archived: demotion is about reference
    material.
    """
    if not doc:
        return False
    return doc.get("type") == "reference" or doc.get("status") == "reference"


# Listing order: how much a doc should be trusted to be current, then how
# explicitly a person stood behind it. A missing intent is incidental, so it
# ranks with incidental; the line still reads Unattributed. A retired status
# ranks with living.
_STATUS_RANK = {"living": 0, "deprecated": 1, "reference": 2}
_INTENT_RANK = {"requested": 0, "chosen": 1, "incidental": 2, None: 2}


def rank_key(doc: dict | None) -> tuple[int, int]:
    """Sort key every listing shares: status, then intent; relevance and id break ties.

    Archived (reference type or status) ranks as reference so a `type: reference`
    doc that is still `living` lands last, as `find` has always put it.
    """
    doc = doc or {}
    status = "reference" if is_archived(doc) else doc.get("status")
    return (_STATUS_RANK.get(status, 0), _INTENT_RANK.get(doc.get("intent"), 2))


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
    "intent": "restructure",
    "intent_basis": "restructure",
    "force": "restructure",
    "realization": "restructure",
    "realization_refs": "restructure",
    "realization_verified": "restructure",
    "imposed_by": "restructure",
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
    """Return the '<Intent> <type>: <Title>' display string for a doc dict.

    The intent leads so a reader sees how explicitly a person stood behind the
    claim before its title. A doc with no intent is shown as 'Unattributed'
    so the gap is visible, and it weighs as incidental. A reference carries
    no intent by type, so it keeps 'Reference: <Title>'.
    Force, realization and lifecycle are not here: they trail the display (see
    ``facet_tags``) so a '[[id|display]]' alias stays a readable name.
    """
    t = doc.get("type", "?")
    title = doc.get("title", doc.get("id", "?"))
    if t == "reference":
        return f"Reference: {title}"
    intent = (doc.get("intent") or "unattributed").capitalize()
    return f"{intent} {t}: {title}"


def facet_tags(doc: dict) -> str:
    """The ' · must · planned' tail naming how hard a doc binds and whether it exists.

    Empty when the doc carries neither, so the facets a type forbids never show.
    Takes any mapping with `force` / `realization` keys, so a record and a parsed
    doc render the same tail.
    """
    return "".join(f" · {v}" for v in (doc.get("force"), doc.get("realization")) if v)


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
    Render a stored '[[<id>]]' for human display as '[[<id>|<Intent> <type>: <Title>]]'.

    The label is resolved live from the current doc, so display always reflects
    the doc's present title. A missing target renders explicitly rather than
    silently dropping the ref. The |alias form is also what Obsidian shows.
    """
    if doc is None:
        return f"[[{doc_id}|(missing)]]"
    return f"[[{doc_id}|{display_label(doc)}]]"


def successor_displays(doc: dict, docs: dict) -> list[dict]:
    """The docs a deprecated doc points at, as [{id, display}] for its line.

    A successor missing from `docs` shows as its bare id: the line stays honest
    about a replacement it cannot name.
    """
    return [
        {"id": sid, "display": display_label(docs[sid]) if sid in docs else sid}
        for sid in doc.get("superseded_by", [])
    ]


def doc_prefix(doc: dict) -> str:
    """Return the '<id> [<label>] "<Type>: <Title>"' human prefix for a doc dict."""
    doc_id = doc.get("id", "<unknown>")
    label = doc.get("label", "") or "(no label)"
    return f'{doc_id} [{label}] "{display_label(doc)}"'
