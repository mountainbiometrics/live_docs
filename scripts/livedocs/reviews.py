"""
reviews.py — Review-summary ledger for live_docs.

A review summary is process state (not knowledge), so it lives in a separate
reviews/ tier, never in docs/. The knowledge graph is unaffected: validate,
reindex, and edges still operate only on docs/.

Public API:
    ReviewLedger    — load, create, sign, list, show review records
    parse_review    — parse a single reviews/<id>.md file
    dump_review     — serialize a review record to its on-disk format

Record format (reviews/<id>.md):
    ---
    id: "<id>"
    created: "<iso8601>"
    touched: ["[[<doc_id>]]", ...]
    signoffs:
      - who: "<name>"
        at: "<iso8601>"
    ---

    ## Additions
    - [[<id>]]
      <Context or Overview section, indented>
    ## Revisions
    - [[<id>]] — <what changed>
    ## Minor Alterations
    - <note>

Refs are stored as bare '[[<id>]]' tokens (the id is the only source of
truth); labels are resolved live at display time via ReviewLedger.render_body.

Stdlib only. No external dependencies.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .model import generate_id, ref_token, render_ref_token, session_start_iso, WIKILINK_RE


def _normalize_ref(token: str) -> str:
    """Reduce a touched-ref token to its bare id.

    Accepts the canonical on-disk form '[[<id>]]' (or '[[<id>|label]]') and
    the legacy bare-id form, returning just '<id>'. Tolerant of stray
    whitespace and quoting so it round-trips any pre-migration file.
    """
    token = str(token).strip()
    m = WIKILINK_RE.search(token)
    if m:
        return m.group(1)
    return token
from .serialize import _yaml_str, _yaml_wikilink_list, _parse_frontmatter_text


# ---------------------------------------------------------------------------
# Body section extraction for review summaries
# ---------------------------------------------------------------------------

def _section_heading_match(line: str, names: tuple[str, ...]) -> bool:
    """True when line is a ## heading whose name matches one of `names`."""
    if not line.startswith("## "):
        return False
    heading = line[3:].strip()
    return any(
        heading == name
        or heading.startswith(f"{name} ")
        or heading.startswith(f"{name}/")
        for name in names
    )


def _extract_body_section(body: str, headings: tuple[str, ...]) -> str:
    """
    Return trimmed content of the first matching ## section in `body`.

    Matches exact headings and variants like "## Context / Origin".
    """
    if not body:
        return ""

    lines = body.splitlines()
    in_section = False
    collected: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if in_section:
                break
            if _section_heading_match(line, headings):
                in_section = True
            continue
        if in_section:
            collected.append(line)

    while collected and not collected[0].strip():
        collected.pop(0)
    while collected and not collected[-1].strip():
        collected.pop()

    return "\n".join(collected)


# ---------------------------------------------------------------------------
# WAL archive: a non-rendered block folded into the review at close
# ---------------------------------------------------------------------------
#
# The raw session WAL is preserved losslessly inside the review file, wrapped in
# HTML-comment delimiters so `ldoc review show` and the viewer skip it by
# default (on-disk-session-records). Nothing is lost; the block is not part of
# the human-facing summary.

import json as _json

_WAL_ARCHIVE_BEGIN = "<!-- WAL-ARCHIVE"
_WAL_ARCHIVE_END = "WAL-ARCHIVE-END -->"


def _archive_wal_block(wal: list[dict]) -> str:
    """Render the raw WAL as a non-rendered, HTML-comment-delimited block."""
    lines = [_WAL_ARCHIVE_BEGIN]
    lines.append("Raw session change log (WAL) — source of truth, not rendered.")
    for entry in wal:
        lines.append(_json.dumps(entry, ensure_ascii=False))
    lines.append(_WAL_ARCHIVE_END)
    return "\n".join(lines)


def strip_wal_archive(body: str) -> str:
    """Return `body` with the trailing WAL-archive comment block removed.

    Used by `review show` and the viewer so the archive never renders.
    """
    if _WAL_ARCHIVE_BEGIN not in body:
        return body
    start = body.find(_WAL_ARCHIVE_BEGIN)
    end = body.find(_WAL_ARCHIVE_END)
    if end != -1:
        end += len(_WAL_ARCHIVE_END)
        return (body[:start] + body[end:]).rstrip() + "\n"
    # Unterminated — drop everything from the marker on.
    return body[:start].rstrip() + "\n"


def _doc_created_at(doc: dict) -> str:
    """A doc's creation time — the timestamp of its leading `addition` history entry.

    The `created` frontmatter field was removed (creation-is-recorded-history):
    creation is now the first history entry, which is an addition. Falls back to
    a legacy `created` field for any doc that predates the migration.
    """
    hist = doc.get("history") or []
    if hist and "addition" in (hist[0].get("change_type") or []):
        return hist[0].get("at", "")
    return doc.get("created", "")


def _format_addition_entry(link: str, doc: dict) -> list[str]:
    """Render one Additions list item with a nested per-doc blurb.

    Prefer the doc's frontmatter `summary` when present; fall back to the
    body's Context/Overview section so reviews built before the summary field
    existed still render their blurb.
    """
    summary = (doc.get("summary") or "").strip()
    blurb = summary or _extract_body_section(doc.get("body", "") or "", ("Context", "Overview"))
    lines = [f"- {link}"]
    if blurb:
        for line in blurb.splitlines():
            lines.append(f"  {line}")
    return lines


# ---------------------------------------------------------------------------
# Parse / dump for review records
# ---------------------------------------------------------------------------

def parse_review(path: Path) -> dict:
    """
    Parse a reviews/<id>.md file into a dict:
        id, created, touched (list), signoffs (list of {who, at}), body
    """
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)

    if len(parts) < 3:
        return {"id": path.stem, "created": "", "touched": [], "signoffs": [], "body": text}

    fm = _parse_frontmatter_text(parts[1])
    body = parts[2].lstrip("\n")

    # Normalize touched to a list of bare ids (the in-memory representation).
    # On disk, touched is stored as canonical "[[<id>]]" wiki-links (matching
    # the frontmatter edge convention); strip the wrapping here so all
    # downstream logic — membership checks, counts, body rendering — works on
    # bare ids regardless of whether a given file predates the migration.
    touched = fm.get("touched", [])
    if not isinstance(touched, list):
        touched = [touched] if touched else []
    fm["touched"] = [_normalize_ref(t) for t in touched]

    # Normalize signoffs to list of {who, at} dicts
    signoffs = fm.get("signoffs", [])
    if not isinstance(signoffs, list):
        signoffs = []
    # Each item should be a dict; filter/normalize
    clean = []
    for s in signoffs:
        if isinstance(s, dict):
            clean.append({"who": s.get("who", ""), "at": s.get("at", "")})
    fm["signoffs"] = clean

    fm["id"] = path.stem
    fm["body"] = body
    return fm


def dump_review(fm: dict, body: str) -> str:
    """
    Serialize a review record to its on-disk format.

    Frontmatter fields emitted: id, created, touched, signoffs.
    Body is preserved byte-for-byte.
    """
    lines = ["---"]
    lines.append(f"id: {_yaml_str(fm.get('id', ''))}")
    lines.append(f"created: {_yaml_str(fm.get('created', ''))}")

    # Emit touched as canonical "[[<id>]]" wiki-links, matching the
    # frontmatter edge convention. Tokens are normalized to bare ids first so
    # an already-wrapped in-memory value never gets double-wrapped.
    touched = [_normalize_ref(t) for t in fm.get("touched", [])]
    lines.append(f"touched: {_yaml_wikilink_list(touched)}")

    signoffs = fm.get("signoffs", [])
    if not signoffs:
        lines.append("signoffs: []")
    else:
        lines.append("signoffs:")
        for entry in signoffs:
            lines.append(f"  - who: {_yaml_str(entry.get('who', ''))}")
            lines.append(f"    at: {_yaml_str(entry.get('at', ''))}")

    lines.append("---")

    fm_block = "\n".join(lines)

    if body:
        text = fm_block + "\n\n" + body
    else:
        text = fm_block + "\n"

    if not text.endswith("\n"):
        text += "\n"

    return text


# ---------------------------------------------------------------------------
# ReviewLedger
# ---------------------------------------------------------------------------

class ReviewLedger:
    """
    Query/mutation layer over the reviews/ ledger.

    Parallel to KB but entirely separate: never touches docs/, never enters
    the dependency graph. All review records live in REVIEWS_DIR.
    """

    def __init__(self, reviews_dir: Path | None = None, docs_dir: Path | None = None):
        if reviews_dir is None:
            from .model import REVIEWS_DIR
            reviews_dir = REVIEWS_DIR
        if docs_dir is None:
            from .model import DOCS_DIR
            docs_dir = DOCS_DIR
        self.reviews_dir = reviews_dir
        self.docs_dir = docs_dir
        reviews_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_docs(self) -> dict:
        """Load all docs from docs_dir (used when building summaries)."""
        from .serialize import parse_doc
        result = {}
        for path in sorted(self.docs_dir.glob("*.md")):
            if ".index" in path.parts:
                continue
            doc = parse_doc(path)
            result[doc["id"]] = doc
        return result

    def _load_all_reviews(self) -> dict:
        """Load every review record from reviews_dir. Returns {id: record}."""
        result = {}
        for path in sorted(self.reviews_dir.glob("*.md")):
            if path.name == ".gitkeep":
                continue
            rec = parse_review(path)
            result[rec["id"]] = rec
        return result

    def _resolve(self, ref: str, records: dict) -> str:
        """
        Resolve a ref to a review record id.

        Accepts: exact id, or unique prefix/substring of id.
        Raises ValueError if ambiguous or not found.
        """
        if ref in records:
            return ref

        # Prefix match
        prefix_matches = [rid for rid in records if rid.startswith(ref)]
        if len(prefix_matches) == 1:
            return prefix_matches[0]
        if len(prefix_matches) > 1:
            raise ValueError(
                f"Ambiguous review ref {ref!r} — matches: {', '.join(sorted(prefix_matches))}"
            )

        # Substring match
        sub_matches = [rid for rid in records if ref in rid]
        if len(sub_matches) == 1:
            return sub_matches[0]
        if len(sub_matches) > 1:
            raise ValueError(
                f"Ambiguous review ref {ref!r} — multiple substring matches: "
                f"{', '.join(sorted(sub_matches))}"
            )

        raise ValueError(f"No review record found for ref: {ref!r}")

    # ------------------------------------------------------------------
    # new — create a review summary record
    # ------------------------------------------------------------------

    def new(
        self,
        since: str = "",
        touched_refs: list[str] = None,
        body: str = "",
        session: str = "",
        summary_text: str = "",
        wal: list[dict] | None = None,
    ) -> tuple[str, str]:
        """
        Create a new review summary record.

        With `wal` (the open session's change log): build the review directly
        from the WAL — the source of truth (session-change-log). Sections mirror
        the change-type taxonomy (Additions / Revisions / Restructure /
        Organizational / Deletions); each doc is filed ONCE under its dominant
        change_type. The raw WAL is folded losslessly into a non-rendered block
        at the tail. This is the primary path at `session close`.

        With `session` (an id from `ldoc session start`): the legacy tag-scan
        path — Revisions are docs whose history carries the tag; Additions are
        docs created within the session's window. Retained as a fallback.

        With `since` (ISO 8601 UTC string): scan docs/ to classify Additions
        and Revisions since that timestamp, build the body automatically.

        With `touched_refs` (list of doc ids): build a skeleton summary from
        those docs (used when caller provides explicit touched list).

        With explicit `body`: use that body as-is (no scanning).

        `summary_text`, when given, is prepended as a `## Summary` block — the
        session's agent-recap.

        Returns (review_id, path_str).
        """
        docs = self._load_docs()
        created_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        review_id = generate_id(self.reviews_dir)

        touched: list[str] = []
        wal_archive = ""

        if wal is not None and not body:
            body = self._build_body_from_wal(wal, docs)
            touched = self._collect_touched_from_wal(wal, docs)
            wal_archive = _archive_wal_block(wal)
        elif session and not body:
            body = self._build_body_by_session(session, docs)
            touched = self._collect_touched_by_session(session, docs)
        elif since and not body:
            body = self._build_body_since(since, docs)
            touched = self._collect_touched_since(since, docs)
        elif touched_refs is not None and not body:
            # Explicit touched list, no --summary provided. Normalize so callers
            # may pass bare ids or canonical "[[<id>]]" wiki-links.
            touched = [r for r in (_normalize_ref(t) for t in touched_refs) if r in docs]
            body = self._build_body_from_touched(touched, docs)
        elif touched_refs is not None:
            # Explicit touched list + explicit body
            touched = [r for r in (_normalize_ref(t) for t in touched_refs) if r in docs]
        elif body:
            # Pure explicit body, no touched inference
            touched = []
        # else: empty record

        if summary_text:
            body = f"## Summary\n\n{summary_text.strip()}\n\n{body}"

        if wal_archive:
            body = f"{body.rstrip()}\n\n{wal_archive}\n"

        fm = {
            "id": review_id,
            "created": created_now,
            "touched": touched,
            "signoffs": [],
        }

        path = self.reviews_dir / f"{review_id}.md"
        path.write_text(dump_review(fm, body), encoding="utf-8")
        return review_id, str(path)

    # ------------------------------------------------------------------
    # WAL-based body building (primary path at session close)
    # ------------------------------------------------------------------

    def _collect_touched_from_wal(self, wal: list[dict], docs: dict) -> list[str]:
        """Return the distinct doc ids referenced by the WAL, in first-seen order.

        Deletions ARE included even though the doc no longer exists in docs/ —
        the WAL is the only record of them (session-change-log).
        """
        seen: list[str] = []
        seen_set: set[str] = set()
        for entry in wal:
            ref = entry.get("ref", "")
            if ref and ref not in seen_set:
                seen_set.add(ref)
                seen.append(ref)
        return seen

    def _build_body_from_wal(self, wal: list[dict], docs: dict) -> str:
        """Build the five-section review body from the session WAL.

        Each doc is filed ONCE under its dominant change_type by precedence
        deletion > addition > revision > restructure > organizational, computed
        over the UNION of every WAL line's change_type list for that doc — so a
        doc never appears in two sections. Empty sections are omitted entirely.
        The best available author note per doc is used as the change blurb.
        """
        # Collapse the WAL into one record per doc (dominant type + best note +
        # captured label/type for deletions) — the same projection the per-doc
        # history uses, so review sections and doc history never diverge.
        from .sessions import collapse_wal_per_doc

        agg, order = collapse_wal_per_doc(wal)

        # Bucket each doc under its single dominant type.
        buckets: dict[str, list[str]] = {
            "addition": [], "revision": [], "restructure": [],
            "organizational": [], "deletion": [],
        }
        for ref in order:
            dom = agg[ref].get("dominant", "")
            if dom in buckets:
                buckets[dom].append(ref)

        # Emit only non-empty sections, in canonical order. Each doc appears in
        # exactly one section (its dominant type), so there are no duplicates.
        blocks: list[str] = []
        for heading, key in (
            ("Additions", "addition"),
            ("Revisions", "revision"),
            ("Restructure", "restructure"),
            ("Organizational", "organizational"),
            ("Deletions", "deletion"),
        ):
            refs = buckets[key]
            if not refs:
                continue
            block = [f"## {heading}"]
            for ref in refs:
                if key == "addition":
                    if ref in docs:
                        block.extend(_format_addition_entry(ref_token(ref), docs[ref]))
                    else:
                        block.append(f"- {ref_token(ref)}")
                elif key == "deletion":
                    rec = agg[ref]
                    label = rec.get("label") or ref
                    dtype = rec.get("type") or ""
                    desc = f"{dtype}: {label}" if dtype else label
                    note = rec["note"]
                    base = f"- {ref_token(ref)} ({desc})"
                    block.append(f"{base} — {note}" if note else base)
                else:
                    note = agg[ref]["note"]
                    link = ref_token(ref)
                    block.append(f"- {link} — {note}" if note else f"- {link}")
            blocks.append("\n".join(block))

        body = "\n\n".join(blocks) if blocks else "(no changes recorded)"
        return body + "\n"

    def _collect_touched_since(self, since: str, docs: dict) -> list[str]:
        """
        Return ids of docs created >= since OR with a history entry at >= since
        (but created before since).
        """
        touched = []
        for doc_id, doc in sorted(docs.items()):
            created = _doc_created_at(doc)
            if created >= since:
                touched.append(doc_id)
                continue
            for h in doc.get("history", []):
                if h.get("at", "") >= since:
                    touched.append(doc_id)
                    break
        return touched

    def _build_body_since(self, since: str, docs: dict) -> str:
        """
        Build the three-section summary body by scanning docs since `since`.

        Additions: doc created >= since
        Revisions: doc with history entry at >= since (and created before since)
        Minor Alterations: (not auto-detected; placeholder if none)
        """
        additions: list[str] = []
        revisions: list[str] = []

        for doc_id, doc in sorted(docs.items()):
            created = _doc_created_at(doc)
            if created >= since:
                additions.append(doc_id)
                continue
            for h in doc.get("history", []):
                if h.get("at", "") >= since:
                    revisions.append(doc_id)
                    break

        # Emit only non-empty sections (coarse fallback: additions vs revisions).
        blocks: list[str] = []
        if additions:
            block = ["## Additions"]
            for doc_id in additions:
                block.extend(_format_addition_entry(ref_token(doc_id), docs[doc_id]))
            blocks.append("\n".join(block))
        if revisions:
            block = ["## Revisions"]
            for doc_id in revisions:
                doc = docs[doc_id]
                link = ref_token(doc_id)
                # Use the most recent history entry at >= since as the summary.
                last_summary = ""
                for h in reversed(doc.get("history", [])):
                    if h.get("at", "") >= since:
                        last_summary = h.get("summary", "")
                        break
                block.append(f"- {link} — {last_summary}" if last_summary else f"- {link}")
            blocks.append("\n".join(block))

        body = "\n\n".join(blocks) if blocks else "(no changes recorded)"
        return body + "\n"

    def _collect_touched_by_session(self, session: str, docs: dict) -> list[str]:
        """Return ids of docs created within the session's window OR carrying a
        history entry tagged with this session id.

        Revisions are matched by the exact session tag; Additions fall back to
        the session's own start-time window because a freshly-created doc has no
        history entry to stamp (history-is-changes).
        """
        start = session_start_iso(session)
        touched = []
        for doc_id, doc in sorted(docs.items()):
            if start and doc.get("created", "") >= start:
                touched.append(doc_id)
                continue
            for h in doc.get("history", []):
                if h.get("session", "") == session:
                    touched.append(doc_id)
                    break
        return touched

    def _build_body_by_session(self, session: str, docs: dict) -> str:
        """Build the three-section summary body by exact session tag.

        Additions: doc created within the session window (created >= start).
        Revisions: doc with a history entry tagged with this session id.
        Minor Alterations: not auto-detected (placeholder).
        """
        start = session_start_iso(session)
        additions: list[str] = []
        revisions: list[tuple[str, str]] = []

        for doc_id, doc in sorted(docs.items()):
            if start and doc.get("created", "") >= start:
                additions.append(doc_id)
                continue
            # Most recent history entry stamped with this session becomes the summary.
            last_summary = ""
            for h in reversed(doc.get("history", [])):
                if h.get("session", "") == session:
                    last_summary = h.get("summary", "")
                    break
            if last_summary or any(h.get("session", "") == session for h in doc.get("history", [])):
                revisions.append((doc_id, last_summary))

        lines = []
        lines.append("## Additions")
        if additions:
            for doc_id in additions:
                lines.extend(_format_addition_entry(ref_token(doc_id), docs[doc_id]))
        else:
            lines.append("(none)")

        lines.append("")
        lines.append("## Revisions")
        if revisions:
            for doc_id, last_summary in revisions:
                link = ref_token(doc_id)
                if last_summary:
                    lines.append(f"- {link} — {last_summary}")
                else:
                    lines.append(f"- {link}")
        else:
            lines.append("(none)")

        lines.append("")
        lines.append("## Minor Alterations")
        lines.append("(none)")

        return "\n".join(lines) + "\n"

    def _build_body_from_touched(self, touched: list[str], docs: dict) -> str:
        """Build a skeleton summary body from an explicit touched list."""
        lines = []
        lines.append("## Additions")
        if touched:
            for doc_id in touched:
                if doc_id in docs:
                    lines.extend(_format_addition_entry(ref_token(doc_id), docs[doc_id]))
        else:
            lines.append("(none)")

        lines.append("")
        lines.append("## Revisions")
        lines.append("(none)")

        lines.append("")
        lines.append("## Minor Alterations")
        lines.append("(none)")

        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # list
    # ------------------------------------------------------------------

    def list_reviews(self, unsigned_by: str = "") -> list[dict]:
        """
        Return list of review records as summary dicts.

        Each item: {id, created, touched_count, signers (list of who strings)}

        With unsigned_by: only records where `who` has NOT signed (exact
        case-insensitive match against signoff entries).
        """
        records = self._load_all_reviews()
        result = []

        for rec_id, rec in sorted(records.items()):
            signers = [s.get("who", "") for s in rec.get("signoffs", [])]

            if unsigned_by:
                unsigned_by_lower = unsigned_by.lower()
                already_signed = any(s.lower() == unsigned_by_lower for s in signers)
                if already_signed:
                    continue

            result.append({
                "id": rec_id,
                "created": rec.get("created", ""),
                "touched_count": len(rec.get("touched", [])),
                "signers": signers,
            })

        return result

    # ------------------------------------------------------------------
    # show
    # ------------------------------------------------------------------

    def show(self, ref: str) -> dict:
        """
        Return full review record for ref (id or prefix/substring).

        Returns: {id, created, touched, signoffs, body}
        """
        records = self._load_all_reviews()
        rec_id = self._resolve(ref, records)
        return records[rec_id]

    def render_body(self, body: str) -> str:
        """
        Expand stored '[[<id>]]' refs into '[[<id>|<Type>: <Title>]]' using the
        docs' *current* labels. This is the read-time presentation step that
        keeps the on-disk ledger normalized while display stays human-readable.

        The trailing WAL-archive block is stripped so it never renders.
        """
        body = strip_wal_archive(body or "")
        if not body or "[[" not in body:
            return body
        docs = self._load_docs()

        def repl(m) -> str:
            doc_id = m.group(1)
            return render_ref_token(doc_id, docs.get(doc_id))

        return WIKILINK_RE.sub(repl, body)

    # ------------------------------------------------------------------
    # sign
    # ------------------------------------------------------------------

    def sign(self, ref: str, who: str) -> str:
        """
        Append {who, at: <now-utc-iso>} to a review record's signoffs.

        Returns the signoff timestamp.
        """
        records = self._load_all_reviews()
        rec_id = self._resolve(ref, records)
        path = self.reviews_dir / f"{rec_id}.md"

        rec = records[rec_id]
        body = rec.pop("body", "")

        at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        signoffs = rec.get("signoffs", [])
        signoffs.append({"who": who, "at": at})
        rec["signoffs"] = signoffs

        path.write_text(dump_review(rec, body), encoding="utf-8")
        return at
