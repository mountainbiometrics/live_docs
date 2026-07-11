"""
viewer.py — Build the self-contained, read-only HTML viewer for a live_docs store.

Export contract: each doc becomes a JSON object that is literally its frontmatter
plus one added field `body` (raw markdown). Reviews export the same way. Markdown
and wiki-link resolution run client-side in the generated HTML.

Reads doc files directly rather than through KB porcelain — a one-shot static
export where frontmatter on disk is the contract.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
from pathlib import Path

from ._paths import CONFIG_FILENAME
from .model import DOCS_DIR, REVIEWS_DIR, STORE_ROOT
from .serialize import parse_doc
from .toml_flat import parse_config

AUTO_VIEWER_ENV = "LIVEDOCS_AUTO_VIEWER"
AUTO_VIEWER_VERBOSE_ENV = "LIVEDOCS_AUTO_VIEWER_VERBOSE"

# Packaged assets ship with the tooling, not inside the store.
_VIEWER_DIR = Path(__file__).resolve().parent.parent / "viewer"
_TEMPLATE = _VIEWER_DIR / "template.html"
_MARKED_JS = _VIEWER_DIR / "vendor" / "marked.min.js"

_WIKILINK_RE = re.compile(r"\[\[(\d+)\]\]")


def _load_dir(path: Path) -> list[dict]:
    """Load all .md files in a directory into export records."""
    out: list[dict] = []
    if not path.is_dir():
        return out
    for md_path in sorted(path.glob("*.md")):
        parsed = parse_doc(md_path)
        body = parsed.pop("body", "")
        if isinstance(body, str):
            body = body.strip()
        rec = dict(parsed)
        rec["id"] = str(rec.get("id", md_path.stem))
        rec["body"] = body
        # The `created` frontmatter field was removed for docs (creation is now
        # the leading `addition` history entry). Re-derive it so the viewer's
        # created badge and Catalog sort keep working. Reviews keep their own
        # `created` field and are untouched.
        if not rec.get("created"):
            hist = rec.get("history") or []
            if hist and "addition" in (hist[0].get("change_type") or []):
                rec["created"] = hist[0].get("at", "")
        out.append(rec)
    return out


def _section_link_ids(body: str, headings: tuple[str, ...]) -> set[str]:
    """Return wiki-link ids from top-level list items in the first matching section."""
    from .reviews import _section_heading_match

    if not body:
        return set()

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

    ids: set[str] = set()
    for line in collected:
        stripped = line.lstrip()
        if not stripped.startswith("- "):
            continue
        for m in _WIKILINK_RE.finditer(line):
            ids.add(m.group(1))
    return ids


def _review_stats(body: str, integration: dict | None = None) -> dict:
    """Compute headline counts for the review card.

    Section counts come from the visible body. Integration edge counts come from
    the mint-time ``integration`` frontmatter snapshot when present — never
    recomputed from the live graph or guessed from WAL organizational lines.
    """
    from .reviews import _extract_body_section, strip_wal_archive

    visible = strip_wal_archive(body)
    summary = _extract_body_section(visible, ("Summary",)).strip()
    new_docs = _section_link_ids(visible, ("Additions",))
    touched_docs = _section_link_ids(visible, ("Revisions", "Restructure"))
    minor_docs = _section_link_ids(visible, ("Minor Alterations", "Organizational"))
    reference_docs = _section_link_ids(visible, ("Reference files",))

    stats = {
        "new_docs": len(new_docs),
        "touched_docs": len(touched_docs),
        "minor_docs": len(minor_docs),
        "reference_docs": len(reference_docs),
        "summary": summary,
    }
    if isinstance(integration, dict):
        stats["new_to_new"] = int(integration.get("new_to_new", 0) or 0)
        stats["new_to_existing"] = int(integration.get("new_to_existing", 0) or 0)
        stats["edges_added_to_existing"] = int(
            integration.get("edges_added_to_existing", 0) or 0
        )
        stats["has_integration"] = True
    else:
        stats["has_integration"] = False
    return stats


def _load_reviews(path: Path) -> list[dict]:
    """Load review records with precomputed stats; WAL stripped from body."""
    from .reviews import parse_review, strip_wal_archive

    out: list[dict] = []
    if not path.is_dir():
        return out
    for md_path in sorted(path.glob("*.md")):
        rec = parse_review(md_path)
        raw_body = rec.get("body", "") or ""
        stats = _review_stats(raw_body, rec.get("integration"))
        body = strip_wal_archive(raw_body)
        if isinstance(body, str):
            body = body.strip()
        rec["body"] = body
        rec["stats"] = stats
        out.append(rec)
    return out


def _load_viewer_config() -> dict:
    """Read optional ``[viewer]`` settings from the store's ``.live_docs.toml``."""
    default: dict = {
        "title": "live_docs",
        "subtitle": "viewer · read-only",
        "domain_colors": {},
        "type_icons": {},
        "favicon": None,
    }
    cfg_path = STORE_ROOT / CONFIG_FILENAME
    if not cfg_path.is_file():
        return default

    try:
        data = parse_config(cfg_path.read_text(encoding="utf-8"))
    except OSError:
        return default

    viewer = data.get("viewer")
    if not isinstance(viewer, dict):
        return default

    out = dict(default)
    for key in ("title", "subtitle"):
        val = viewer.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = val.strip()

    domain_colors = viewer.get("domain_colors") or viewer.get("domains") or {}
    if isinstance(domain_colors, dict):
        out["domain_colors"] = {
            str(k): v for k, v in domain_colors.items()
            if isinstance(v, (str, dict))
        }

    type_icons = viewer.get("type_icons") or viewer.get("types") or {}
    if isinstance(type_icons, dict):
        clean: dict[str, dict] = {}
        for k, v in type_icons.items():
            if isinstance(v, dict):
                clean[str(k)] = {sk: sv for sk, sv in v.items() if isinstance(sv, str)}
            elif isinstance(v, str):
                clean[str(k)] = {"color": v}
        out["type_icons"] = clean

    fav = viewer.get("favicon")
    if isinstance(fav, str) and fav.strip():
        fav_path = Path(fav.strip())
        if not fav_path.is_absolute():
            fav_path = (STORE_ROOT / fav_path).resolve()
        if fav_path.is_file():
            mime = mimetypes.guess_type(fav_path.name)[0] or "image/png"
            encoded = base64.b64encode(fav_path.read_bytes()).decode("ascii")
            out["favicon"] = f"data:{mime};base64,{encoded}"

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
    reviews = _load_reviews(REVIEWS_DIR)
    viewer_config = _load_viewer_config()

    dest = out_path or (STORE_ROOT / "build" / "viewer.html")
    dest = dest.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)

    template = _TEMPLATE.read_text(encoding="utf-8")
    marked_js = _MARKED_JS.read_text(encoding="utf-8")

    html = template.replace("/*__DOCS_JSON__*/", json.dumps(docs, ensure_ascii=False))
    html = html.replace("/*__REVIEWS_JSON__*/", json.dumps(reviews, ensure_ascii=False))
    html = html.replace(
        "/*__VIEWER_CONFIG__*/",
        json.dumps(viewer_config, ensure_ascii=False),
    )
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
