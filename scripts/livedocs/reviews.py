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
    touched: [<doc_id>, ...]
    signoffs:
      - who: "<name>"
        at: "<iso8601>"
    ---

    ## Additions
    - [<Type>: <Title>](<id>.md)
      <Context or Overview section, indented>
    ## Revisions
    - [<Type>: <Title>](<id>.md) — <what changed>
    ## Minor Alterations
    - <note>

Stdlib only. No external dependencies.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .model import REVIEWS_DIR, generate_id, DOCS_DIR, ref_link
from .serialize import _yaml_str, _yaml_list, _parse_frontmatter_text


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


def _format_addition_entry(link: str, doc: dict) -> list[str]:
    """Render one Additions list item with nested Context/Overview content."""
    section = _extract_body_section(doc.get("body", "") or "", ("Context", "Overview"))
    lines = [f"- {link}"]
    if section:
        for line in section.splitlines():
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

    # Normalize touched to list of strings
    touched = fm.get("touched", [])
    if not isinstance(touched, list):
        touched = [touched] if touched else []
    fm["touched"] = touched

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

    touched = fm.get("touched", [])
    lines.append(f"touched: {_yaml_list(touched)}")

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

    def __init__(self, reviews_dir: Path = REVIEWS_DIR, docs_dir: Path = DOCS_DIR):
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
    ) -> tuple[str, str]:
        """
        Create a new review summary record.

        With `since` (ISO 8601 UTC string): scan docs/ to classify Additions
        and Revisions since that timestamp, build the body automatically.

        With `touched_refs` (list of doc ids): build a skeleton summary from
        those docs (used when caller provides explicit touched list).

        With explicit `body`: use that body as-is (no scanning).

        Returns (review_id, path_str).
        """
        docs = self._load_docs()
        created_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        review_id = generate_id(self.reviews_dir)

        touched: list[str] = []

        if since and not body:
            body = self._build_body_since(since, docs)
            touched = self._collect_touched_since(since, docs)
        elif touched_refs is not None and not body:
            # Explicit touched list, no --summary provided
            touched = [r for r in touched_refs if r in docs]
            body = self._build_body_from_touched(touched, docs)
        elif touched_refs is not None:
            # Explicit touched list + explicit body
            touched = [r for r in touched_refs if r in docs]
        elif body:
            # Pure explicit body, no touched inference
            touched = []
        # else: empty record

        fm = {
            "id": review_id,
            "created": created_now,
            "touched": touched,
            "signoffs": [],
        }

        path = self.reviews_dir / f"{review_id}.md"
        path.write_text(dump_review(fm, body), encoding="utf-8")
        return review_id, str(path)

    def _collect_touched_since(self, since: str, docs: dict) -> list[str]:
        """
        Return ids of docs created >= since OR with a history entry at >= since
        (but created before since).
        """
        touched = []
        for doc_id, doc in sorted(docs.items()):
            created = doc.get("created", "")
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
            created = doc.get("created", "")
            if created >= since:
                additions.append(doc_id)
                continue
            for h in doc.get("history", []):
                if h.get("at", "") >= since:
                    revisions.append(doc_id)
                    break

        lines = []
        lines.append("## Additions")
        if additions:
            for doc_id in additions:
                lines.extend(_format_addition_entry(ref_link(docs[doc_id]), docs[doc_id]))
        else:
            lines.append("(none)")

        lines.append("")
        lines.append("## Revisions")
        if revisions:
            for doc_id in revisions:
                doc = docs[doc_id]
                link = ref_link(doc)
                # Use the most recent history entry as summary
                hist = doc.get("history", [])
                last_summary = ""
                # Find the most recent history entry at >= since
                for h in reversed(hist):
                    if h.get("at", "") >= since:
                        last_summary = h.get("summary", "")
                        break
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
                    lines.extend(_format_addition_entry(ref_link(docs[doc_id]), docs[doc_id]))
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
