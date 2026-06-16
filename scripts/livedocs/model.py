"""
model.py — Primitives and constants for the live_docs tooling.

Paths, enum sets, label utilities, and ID generation.
Stdlib only. No external dependencies.
"""

import re
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths — resolved at import time, relative to THIS file's location
# ---------------------------------------------------------------------------

# scripts/livedocs/model.py → scripts/livedocs/ → scripts/ → repo_root
_SCRIPTS_DIR: Path = Path(__file__).resolve().parent.parent
REPO_ROOT: Path = _SCRIPTS_DIR.parent
DOCS_DIR: Path = REPO_ROOT / "docs"
RAW_DIR: Path = REPO_ROOT / "raw"
TEMPLATES_DIR: Path = REPO_ROOT / "templates"


# ---------------------------------------------------------------------------
# Valid enum values
# ---------------------------------------------------------------------------

VALID_TYPES = {
    "type", "principle", "goal", "decision", "constraint",
    "requirement", "use-case", "guide", "component", "reference", "index",
}
VALID_STATUSES = {"living", "historical"}
VALID_LEVELS = {"incidental", "trial", "preference", "requirement"}
VALID_STATES = {"actual", "target"}
VALID_REFERENCE_KINDS = {"brainstorm", "plan", "clipping", "external"}

# Label validation pattern: letters/digits, with single spaces or hyphens
# between tokens (whitespace IS allowed; kebab-case remains valid).
LABEL_RE = re.compile(r'^[A-Za-z0-9]+([ -][A-Za-z0-9]+)*$')


# ---------------------------------------------------------------------------
# Collision-safe ID generation (shared by ld new and ingest_raw.py)
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
    - Lowercase the result and strip trailing punctuation.
    - Does NOT kebab-case: whitespace between words is preserved.
    """
    MAX_LEN = 24
    words = title.split()
    if not words:
        return ""

    chosen: list[str] = [words[0]]
    length = len(words[0])
    for w in words[1:]:
        # +1 accounts for the joining space
        if length + 1 + len(w) > MAX_LEN:
            break
        chosen.append(w)
        length += 1 + len(w)

    label = " ".join(chosen).lower()
    # Strip trailing punctuation (anything that's not a letter/digit) per word end
    label = re.sub(r'[^A-Za-z0-9]+$', '', label)
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


def doc_prefix(doc: dict) -> str:
    """Return the '<id> [<label>] "<Type>: <Title>"' human prefix for a doc dict."""
    doc_id = doc.get("id", "<unknown>")
    label = doc.get("label", "") or "(no label)"
    return f'{doc_id} [{label}] "{display_label(doc)}"'
