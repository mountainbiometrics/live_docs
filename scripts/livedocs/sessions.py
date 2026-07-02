"""
sessions.py — On-disk editing-session records + write-ahead change log (WAL).

An OPEN editing session is a record on disk in a configurable sessions/ box
(parallel to reviews/). Keyed by session id, the record holds:

    - opened_at   the ISO 8601 UTC time the session was opened
    - status      "open" while live (deleted on close)
    - summary     the settable agent-recap (one-line intent of the whole session)
    - WAL         the write-ahead change log: one line per mutation

Every store mutation DOUBLE-WRITES (session-change-log 20260701225016): a per-doc
history entry AND a WAL line to the open session. The WAL is the source of truth
for the review built at close — and the ONLY place deletions are recorded, since
a deletion removes the doc and so leaves no per-doc history.

The session's ID POINTER stays ambient in the environment (LDOC_SESSION); this
module owns only the persisted record, keyed by id (on-disk-session-records
20260701224960).

Record format (sessions/<id>.md):
    ---
    id: "<id>"
    opened_at: "<iso8601>"
    status: "open"
    summary: "<agent recap>"
    ---

    ## Change log (WAL)

    ```json
    {"at": "...", "op": "set", "ref": "<id>", "change_type": ["revision"], "note": "..."}
    {"at": "...", "op": "rm",  "ref": "<id>", "change_type": ["deletion"], "note": "...",
     "label": "...", "type": "...", "stripped_edges": [["<id>", "requires"], ...]}
    ```

WAL lines are stored as one JSON object per line inside a fenced ```json block,
so the log round-trips losslessly and stays greppable.

Stdlib only. No external dependencies.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .model import generate_session_id, change_types_for_fields
from .serialize import _yaml_str, _parse_frontmatter_text


_WAL_FENCE = "```json"
_WAL_HEADING = "## Change log (WAL)"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Parse / dump for a session record
# ---------------------------------------------------------------------------

def parse_session(path: Path) -> dict:
    """Parse a sessions/<id>.md file into a dict:
        id, opened_at, status, summary, wal (list of dicts)
    """
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {"id": path.stem, "opened_at": "", "status": "open",
                "summary": "", "wal": []}

    fm = _parse_frontmatter_text(parts[1])
    body = parts[2]

    wal = _parse_wal_block(body)

    return {
        "id": path.stem,
        "opened_at": fm.get("opened_at", "") or "",
        "status": fm.get("status", "open") or "open",
        "summary": fm.get("summary", "") or "",
        "wal": wal,
    }


def _parse_wal_block(body: str) -> list[dict]:
    """Extract the fenced ```json WAL block; parse one JSON object per line."""
    wal: list[dict] = []
    in_block = False
    for line in body.splitlines():
        stripped = line.strip()
        if not in_block:
            if stripped == _WAL_FENCE:
                in_block = True
            continue
        if stripped == "```":
            break
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
            if isinstance(obj, dict):
                wal.append(obj)
        except json.JSONDecodeError:
            # Tolerate a malformed line rather than losing the whole log.
            continue
    return wal


def dump_session(rec: dict) -> str:
    """Serialize a session record to its on-disk format."""
    lines = ["---"]
    lines.append(f"id: {_yaml_str(rec.get('id', ''))}")
    lines.append(f"opened_at: {_yaml_str(rec.get('opened_at', ''))}")
    lines.append(f"status: {_yaml_str(rec.get('status', 'open'))}")
    lines.append(f"summary: {_yaml_str(rec.get('summary', ''))}")
    lines.append("---")
    lines.append("")
    lines.append(_WAL_HEADING)
    lines.append("")
    lines.append(_WAL_FENCE)
    for entry in rec.get("wal", []):
        lines.append(json.dumps(entry, sort_keys=False, ensure_ascii=False))
    lines.append("```")
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    return text


# ---------------------------------------------------------------------------
# SessionStore — the query/mutation layer over the sessions/ box
# ---------------------------------------------------------------------------

class SessionStore:
    """Query/mutation layer over the sessions/ box.

    Parallel to ReviewLedger: never touches docs/, never enters the dependency
    graph. All open-session records live in SESSIONS_DIR, one per open session
    keyed by id.
    """

    def __init__(self, sessions_dir: Path | None = None):
        if sessions_dir is None:
            from .model import SESSIONS_DIR
            sessions_dir = SESSIONS_DIR
        self.sessions_dir = sessions_dir

    def _path(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.md"

    def exists(self, session_id: str) -> bool:
        return self._path(session_id).is_file()

    def open(self, session_id: str | None = None, summary: str = "") -> str:
        """Create a new open-session record. Returns the session id.

        Mints an id when none is given. Idempotent-safe: raises if the id is
        already an open record (should not happen for freshly-minted ids).
        """
        if session_id is None:
            session_id = generate_session_id()
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        if self.exists(session_id):
            raise ValueError(f"session record already exists: {session_id}")
        rec = {
            "id": session_id,
            "opened_at": _now_iso(),
            "status": "open",
            "summary": summary,
            "wal": [],
        }
        self._path(session_id).write_text(dump_session(rec), encoding="utf-8")
        return session_id

    def get(self, session_id: str) -> dict | None:
        """Return the parsed record for session_id, or None if no record."""
        path = self._path(session_id)
        if not path.is_file():
            return None
        return parse_session(path)

    def append_wal(self, session_id: str, entry: dict) -> None:
        """Append one WAL line to an open session; auto-open if the record is
        missing (an auto-created session whose record was never written)."""
        rec = self.get(session_id)
        if rec is None:
            # Heal: an id is set but the record does not exist yet. Mint it so
            # no change is ever dropped (sessions-are-required auto-create).
            self.open(session_id)
            rec = self.get(session_id)
        rec["wal"].append(entry)
        self._path(session_id).write_text(dump_session(rec), encoding="utf-8")

    def set_summary(self, session_id: str, summary: str) -> None:
        """Set the session's agent-recap summary."""
        rec = self.get(session_id)
        if rec is None:
            raise ValueError(f"no open session record: {session_id}")
        rec["summary"] = summary
        self._path(session_id).write_text(dump_session(rec), encoding="utf-8")

    def list_open(self) -> list[dict]:
        """Return all open session records, sorted by id (oldest first)."""
        if not self.sessions_dir.is_dir():
            return []
        out = []
        for path in sorted(self.sessions_dir.glob("*.md")):
            if path.name == ".gitkeep":
                continue
            rec = parse_session(path)
            if rec.get("status", "open") == "open":
                out.append(rec)
        return out

    def delete(self, session_id: str) -> None:
        """Delete the live record (called at close, after it folds into a review)."""
        path = self._path(session_id)
        if path.is_file():
            path.unlink()

    # ------------------------------------------------------------------
    # merge — fold fragment sessions into the earliest
    # ------------------------------------------------------------------

    def merge(self, session_ids: list[str]) -> tuple[str, list[str]]:
        """Fold the given OPEN sessions into the EARLIEST of them.

        Concatenates their WALs in time order and returns (target_id, others).
        The caller is responsible for re-tagging per-doc history entries and for
        deleting the folded-away records. Raises if any id is not an open record.
        """
        recs = {}
        for sid in session_ids:
            rec = self.get(sid)
            if rec is None or rec.get("status", "open") != "open":
                raise ValueError(f"not an open session: {sid}")
            recs[sid] = rec
        # Earliest by opened_at, then id, as tiebreak.
        target = min(recs, key=lambda s: (recs[s].get("opened_at", ""), s))
        others = [s for s in session_ids if s != target]

        merged_wal = []
        for rec in recs.values():
            merged_wal.extend(rec.get("wal", []))
        merged_wal.sort(key=lambda e: e.get("at", ""))

        target_rec = recs[target]
        target_rec["wal"] = merged_wal
        self._path(target).write_text(dump_session(target_rec), encoding="utf-8")
        for sid in others:
            self.delete(sid)
        return target, others


# ---------------------------------------------------------------------------
# Ambient session resolution + the double-write choke-point
# ---------------------------------------------------------------------------

def resolve_open_session() -> str:
    """Return the currently-open session id from the ambient environment
    (LDOC_SESSION), or '' when none is set."""
    return (os.environ.get("LDOC_SESSION", "") or "").strip()


def ensure_session(store: SessionStore | None = None) -> tuple[str, bool]:
    """Resolve the open session, auto-creating one when absent.

    Returns (session_id, was_auto_created). When LDOC_SESSION is set, the record
    is healed (created) if missing. When unset, a fresh session is minted and a
    record written — the caller announces it (sessions-are-required auto-create).
    """
    if store is None:
        store = SessionStore()
    sid = resolve_open_session()
    if sid:
        if not store.exists(sid):
            store.open(sid)
        return sid, False
    sid = store.open()
    return sid, True


def _print_auto_session_notice(session_id: str) -> None:
    """Announce an auto-created session on stderr (id + export line)."""
    import sys
    sys.stderr.write(
        f"NOTE: no open session — auto-created one to attribute this change.\n"
        f"  session: {session_id}\n"
        f"  export to keep tagging under it (and avoid fragments):\n"
        f"    export LDOC_SESSION={session_id}\n"
    )


def record_doc_change(
    kb,
    ref: str,
    note: str,
    change_type: list[str],
    *,
    auto_note: str = "",
) -> None:
    """The single choke-point for a NON-DELETION doc change.

    Double-writes (session-change-log): appends a per-doc history entry (with
    change_type) AND a WAL line to the open session. Auto-creates + announces a
    session when none is open (sessions-are-required).

    `note` is the author-supplied note (may be empty). `auto_note` is a
    pre-computed obvious-op fallback used only when `note` is empty. The WAL
    marks whether the note was author-supplied so the close-gate can tell a real
    explanation from an auto-fill.
    """
    doc_id = kb.resolve(ref)

    store = SessionStore()
    session_id, was_auto = ensure_session(store)
    if was_auto:
        _print_auto_session_notice(session_id)

    author_supplied = bool(note.strip())
    effective_note = note.strip() or auto_note.strip()

    # Per-doc history entry (session-stamped, change-typed).
    kb.add_history(doc_id, effective_note, session=session_id, change_type=change_type)

    # WAL line.
    entry = {
        "at": _now_iso(),
        "op": "change",
        "ref": doc_id,
        "change_type": list(change_type),
        "note": effective_note,
        "author_note": author_supplied,
    }
    store.append_wal(session_id, entry)


def record_deletion(
    kb,
    doc_id: str,
    label: str,
    doc_type: str,
    stripped_edges: list,
    note: str,
    auto_note: str = "",
) -> str:
    """Record a DELETION in the WAL only (the doc is gone — no per-doc history).

    Captures the dead doc's label/type and the inbound edges that were stripped,
    so the deletion is auditable and replayable (session-change-log). Auto-creates
    a session when none is open. Returns the session id used.
    """
    store = SessionStore()
    session_id, was_auto = ensure_session(store)
    if was_auto:
        _print_auto_session_notice(session_id)

    author_supplied = bool(note.strip())
    effective_note = note.strip() or auto_note.strip()

    entry = {
        "at": _now_iso(),
        "op": "rm",
        "ref": doc_id,
        "change_type": ["deletion"],
        "note": effective_note,
        "author_note": author_supplied,
        "label": label,
        "type": doc_type,
        "stripped_edges": [list(e) for e in (stripped_edges or [])],
    }
    store.append_wal(session_id, entry)
    return session_id


def record_addition(
    kb,
    doc_id: str,
    note: str = "Created doc",
) -> str:
    """Record a doc CREATION: an addition history entry (session-stamped) AND a
    WAL line. Auto-creates a session when none is open. Returns the session id.

    Creation is recorded history (creation-is-recorded-history): the doc's first
    history entry is an addition. The addition is excluded from the churn signal
    downstream.
    """
    store = SessionStore()
    session_id, was_auto = ensure_session(store)
    if was_auto:
        _print_auto_session_notice(session_id)

    kb.add_history(doc_id, note, session=session_id, change_type=["addition"])

    entry = {
        "at": _now_iso(),
        "op": "new",
        "ref": doc_id,
        "change_type": ["addition"],
        "note": note,
        "author_note": False,
    }
    store.append_wal(session_id, entry)
    return session_id
