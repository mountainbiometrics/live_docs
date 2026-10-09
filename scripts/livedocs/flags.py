"""
flags.py — the ledger of flags readers raise on badly written docs.

A flag is process state, like a review: one file per flag in the store's
`flags` box, never in docs/ and never an edge. Raising or resolving one leaves
the doc untouched, so a reader mid-task records the problem and moves on, and
gardening works the open flags later.

Stdlib only. No external dependencies.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .model import generate_id, now_iso, ref_token
from .serialize import _unwrap_wikilink, dump_doc, parse_doc


class FlagLedger:
    """Query/mutation layer over the flags/ ledger; never touches docs/."""

    # See KB.READ_METHODS.
    READ_NAMESPACE = "flag"
    READ_METHODS = ("list",)

    def __init__(self, flags_dir: Path) -> None:
        self.flags_dir = Path(flags_dir)

    def add(self, doc_id: str, reason: str, session: str | None = None) -> dict[str, Any]:
        """Record that a doc is badly written, instead of rewriting it mid-task."""
        self.flags_dir.mkdir(parents=True, exist_ok=True)
        rec = {"id": generate_id(self.flags_dir), "doc": doc_id,
               "at": now_iso(), "reason": " ".join(reason.split())}
        if session:
            rec["session"] = session
        self._write(rec)
        return rec

    def all(self) -> list[dict[str, Any]]:
        return [self._read(p) for p in sorted(self.flags_dir.glob("*.md"))]

    def open(self) -> list[dict[str, Any]]:
        return [r for r in self.all() if "resolved_at" not in r]

    def list(self, include_resolved: bool = False) -> list[dict[str, Any]]:
        """List the flags readers raised on badly written docs, oldest first.

        include_resolved -- also list flags already resolved (default: open only).
        """
        return self.all() if include_resolved else self.open()

    def resolve(self, flag_id: str, note: str) -> dict[str, Any]:
        """Close a flag once gardening has rewritten its doc or kept it as written."""
        rec = next((r for r in self.open() if r["id"] == flag_id), None)
        if rec is None:
            raise ValueError(
                f"No open flag {flag_id!r}. List open flags with: ldoc flag list "
                f"(--all includes resolved ones)"
            )
        rec.update(resolved_at=now_iso(), resolution=" ".join(note.split()))
        self._write(rec)
        return rec

    def open_counts(self) -> Counter[str]:
        return Counter(r["doc"] for r in self.open())

    @staticmethod
    def footer(count: int) -> str:
        if not count:
            return ""
        return f"{count} open flag(s) on badly written docs — see: ldoc flag list"

    def _read(self, path: Path) -> dict[str, Any]:
        rec = {k: v for k, v in parse_doc(path).items() if k != "body"}
        rec["doc"] = _unwrap_wikilink(rec.get("doc", ""))
        return rec

    def _write(self, rec: dict[str, Any]) -> None:
        text = dump_doc({**rec, "doc": ref_token(rec["doc"])}, "")
        (self.flags_dir / f"{rec['id']}.md").write_text(text, encoding="utf-8")
