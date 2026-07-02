"""
viewer.py — Build the self-contained, read-only HTML viewer for a live_docs store.

Export contract: each doc becomes a JSON object that is literally its frontmatter
plus one added field `body` (raw markdown). Reviews export the same way. Markdown
and wiki-link resolution run client-side in the generated HTML.

Reads doc files directly rather than through KB porcelain — a one-shot static
export where frontmatter on disk is the contract.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .model import DOCS_DIR, REVIEWS_DIR, REPO_ROOT
from .serialize import parse_doc

AUTO_VIEWER_ENV = "LIVEDOCS_AUTO_VIEWER"
AUTO_VIEWER_VERBOSE_ENV = "LIVEDOCS_AUTO_VIEWER_VERBOSE"

# Packaged assets ship with the tooling, not inside the store.
_VIEWER_DIR = Path(__file__).resolve().parent.parent / "viewer"
_TEMPLATE = _VIEWER_DIR / "template.html"
_MARKED_JS = _VIEWER_DIR / "vendor" / "marked.min.js"


def _load_dir(path: Path, *, strip_wal: bool = False) -> list[dict]:
    """Load all .md files in a directory into export records.

    strip_wal=True removes the non-rendered WAL-archive block from review bodies
    so the raw session log never surfaces in the viewer (on-disk-session-records).
    """
    out: list[dict] = []
    if not path.is_dir():
        return out
    for md_path in sorted(path.glob("*.md")):
        parsed = parse_doc(md_path)
        body = parsed.pop("body", "")
        if isinstance(body, str):
            if strip_wal:
                from .reviews import strip_wal_archive
                body = strip_wal_archive(body)
            body = body.strip()
        rec = dict(parsed)
        rec["id"] = str(rec.get("id", md_path.stem))
        rec["body"] = body
        out.append(rec)
    return out


def build_viewer(*, out_path: Path | None = None) -> tuple[Path, int, int]:
    """
    Generate viewer.html from the discovered store.

    Returns (output_path, doc_count, review_count).
    """
    if not _TEMPLATE.is_file():
        raise FileNotFoundError(f"viewer template not found: {_TEMPLATE}")
    if not _MARKED_JS.is_file():
        raise FileNotFoundError(f"vendored marked.js not found: {_MARKED_JS}")

    docs = _load_dir(DOCS_DIR)
    reviews = _load_dir(REVIEWS_DIR, strip_wal=True)

    dest = out_path or (REPO_ROOT / "build" / "viewer.html")
    dest = dest.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)

    template = _TEMPLATE.read_text(encoding="utf-8")
    marked_js = _MARKED_JS.read_text(encoding="utf-8")

    html = template.replace("/*__DOCS_JSON__*/", json.dumps(docs, ensure_ascii=False))
    html = html.replace("/*__REVIEWS_JSON__*/", json.dumps(reviews, ensure_ascii=False))
    html = html.replace("/*__MARKED_JS__*/", marked_js)

    dest.write_text(html, encoding="utf-8")
    return dest, len(docs), len(reviews)


def auto_viewer_enabled() -> bool:
    """Return False when auto-rebuild is disabled via LIVEDOCS_AUTO_VIEWER."""
    raw = os.environ.get(AUTO_VIEWER_ENV, "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def auto_rebuild_viewer(*, quiet: bool | None = None) -> Path | None:
    """
    Rebuild the viewer if auto-rebuild is enabled.

    Returns the output path on success, None when skipped or disabled.
    Failures are swallowed — a stale viewer must never break porcelain.
    """
    if not auto_viewer_enabled():
        return None

    if quiet is None:
        quiet = os.environ.get(AUTO_VIEWER_VERBOSE_ENV, "").strip().lower() not in (
            "1",
            "true",
            "yes",
            "on",
        )

    try:
        path, n_docs, n_reviews = build_viewer()
    except (FileNotFoundError, OSError):
        return None

    if not quiet:
        import sys

        print(f"viewer: rebuilt {path} ({n_docs} docs, {n_reviews} reviews)", file=sys.stderr)
    return path
