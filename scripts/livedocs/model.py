"""
model.py — Primitives and constants for the live_docs tooling.

Paths, enum sets, label utilities, and ID generation.
Stdlib only. No external dependencies.
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from ._paths import CONFIG_FILENAME, HOME_CONFIG
from .toml_flat import read_store_keys


# ---------------------------------------------------------------------------
# Paths — located by DISCOVERY, not by where this code lives
# ---------------------------------------------------------------------------
#
# A single installed `ldoc` must operate on whichever store the directory you're
# standing in belongs to, so resolution is anchored to the CURRENT WORKING
# DIRECTORY, not to __file__. Git-style: walk up from the CWD looking for a
# `.live_docs.toml` marker; if none is found in the CWD or any parent, fall
# back to a per-user config at ~/.config/live_docs/config.toml; if neither
# exists, complain and exit.
#
# Paths inside a config file resolve relative to the directory CONTAINING that
# file (absolute and ~ paths are kept as-is). So a config can point at docs that
# live in a different repo entirely — a shared "mono-doc" store for several
# related code repos.

# Built-in defaults, used for any key a located config omits. Relative to the
# config file's own directory (the store root).
_DEFAULT_PATHS = {
    "docs": "docs",
    "raw": "raw",
    "reviews": "reviews",
    "inbox": "inbox",
    "index": None,  # None → derived as <docs>/.index
}

# Per-key env var overrides (win over the config file). Relative values resolve
# against the CWD, since they are invocation-time overrides.
_ENV_VARS = {
    "docs": "LIVEDOCS_DOCS_DIR",
    "raw": "LIVEDOCS_RAW_DIR",
    "reviews": "LIVEDOCS_REVIEWS_DIR",
    "inbox": "LIVEDOCS_INBOX_DIR",
}


class LivedocsConfigError(Exception):
    """No live_docs config could be located by discovery."""


def _find_config() -> "tuple[Path | None, list[Path]]":
    """Locate the governing config file.

    Returns (config_path, searched): the chosen file (or None if none exists)
    and every location inspected, so a failure can show its work.
    """
    searched: list[Path] = []
    cwd = Path.cwd().resolve()
    for d in (cwd, *cwd.parents):
        candidate = d / CONFIG_FILENAME
        searched.append(candidate)
        if candidate.is_file():
            return candidate, searched
    searched.append(HOME_CONFIG)
    if HOME_CONFIG.is_file():
        return HOME_CONFIG, searched
    return None, searched


def _resolve_path(value: str, base: Path) -> Path:
    """Resolve a configured path string relative to `base` (absolute/~ kept as-is)."""
    p = Path(value).expanduser()
    return p if p.is_absolute() else (base / p)


def _resolve() -> dict:
    """Run discovery and resolve every store directory. Raises on no config."""
    config_path, searched = _find_config()
    cwd = Path.cwd().resolve()

    if config_path is None:
        # Escape hatch: explicit env overrides can operate without a marker file
        # (e.g. CI). Otherwise there is no store to point at — complain.
        if not any(os.environ.get(v) for v in _ENV_VARS.values()):
            looked = "\n".join(f"  - {p}" for p in searched)
            raise LivedocsConfigError(
                f"no live_docs config found.\n"
                f"Looked for '{CONFIG_FILENAME}' in the current directory and each "
                f"parent, then for a home config:\n{looked}\n"
                f"Create a '{CONFIG_FILENAME}' at your store root, or set a "
                f"LIVEDOCS_* override."
            )
        base = cwd
        config: dict = {}
    else:
        base = config_path.parent
        try:
            config = read_store_keys(config_path)
        except (OSError, ValueError) as e:
            raise LivedocsConfigError(f"could not read config {config_path}: {e}")

    resolved: dict = {"root": base}
    for key in ("docs", "raw", "reviews", "inbox"):
        env_val = os.environ.get(_ENV_VARS[key])
        if env_val:
            resolved[key] = _resolve_path(env_val, cwd)
        elif config.get(key):
            resolved[key] = _resolve_path(str(config[key]), base)
        else:
            resolved[key] = base / _DEFAULT_PATHS[key]

    # Index cache derives under docs by default; an explicit `index` key
    # (config only — no env var) overrides it.
    if config.get("index"):
        resolved["index"] = _resolve_path(str(config["index"]), base)
    else:
        resolved["index"] = resolved["docs"] / ".index"
    return resolved


_resolved_paths: dict | None = None

_PATH_ATTRS: dict[str, str] = {
    "REPO_ROOT": "root",
    "DOCS_DIR": "docs",
    "RAW_DIR": "raw",
    "REVIEWS_DIR": "reviews",
    "INBOX_DIR": "inbox",
    "INDEX_DIR": "index",
}


def _get_paths() -> dict:
    global _resolved_paths
    if _resolved_paths is None:
        try:
            _resolved_paths = _resolve()
        except LivedocsConfigError as e:
            sys.stderr.write(f"ldoc: {e}\n")
            sys.exit(2)
    return _resolved_paths


def __getattr__(name: str) -> "Path":
    if name in _PATH_ATTRS:
        obj = _get_paths()[_PATH_ATTRS[name]]
        globals()[name] = obj  # cache so subsequent access skips __getattr__
        return obj
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
