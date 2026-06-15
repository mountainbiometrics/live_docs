#!/usr/bin/env python3
"""
ingest_raw.py — Write verbatim content into the raw/ tier (Tier 0).

The raw/ directory lives at the repo root, OUTSIDE docs/.  Files in raw/ are
immutable archival originals and are NEVER loaded into the live_docs graph.

Usage:
    python scripts/ingest_raw.py --from-file <path> --source "<origin>"
    python scripts/ingest_raw.py --body "inline text" --source "<origin>"
    echo "text" | python scripts/ingest_raw.py --body - --source "<origin>"

Required:
    --source <str>      Where the content came from (URL, file path, description).

Content (exactly one of):
    --from-file <path>  Read verbatim body from this file.
    --body <str>        Inline body string; use '-' to read from stdin.

Optional:
    --title <str>       Human-readable label stored in the frontmatter header only.

Output (on stdout):
    id:   <YYYYMMDDHHMMSS>
    path: <absolute path to raw/<id>.md>

Stdlib only. No third-party dependencies.
"""

import argparse
import sys
from datetime import date, timezone, datetime
from pathlib import Path

# Ensure scripts/ is on sys.path so livedocs is importable from any CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from livedocs import RAW_DIR, generate_id


# ---------------------------------------------------------------------------
# Frontmatter builder
# ---------------------------------------------------------------------------

def _yaml_str(value: str) -> str:
    """Wrap value in double-quotes, escaping any inner double-quotes."""
    return '"' + value.replace('"', '\\"') + '"'


def build_raw_frontmatter(
    raw_id: str,
    source: str,
    title: str,
    imported: str,
) -> str:
    """
    Return the minimal frontmatter block for a raw/ file.

    Fields emitted:
      id, type, kind, status, original_source, imported
    and optionally title when non-empty.  No depends_on, no tags, no history —
    raw files are not graph nodes and do not need those fields.
    """
    lines = ["---", f"id: {_yaml_str(raw_id)}"]
    if title:
        lines.append(f"title: {_yaml_str(title)}")
    lines += [
        "type: reference",
        "kind: clipping",
        "status: historical",
        f"original_source: {_yaml_str(source)}",
        f"imported: {_yaml_str(imported)}",
        "---",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Body resolution
# ---------------------------------------------------------------------------

def resolve_body(args: argparse.Namespace) -> str:
    """
    Return the verbatim body text from whichever source was specified.
    Does NOT strip or reformat — preservation is the whole point of Tier 0.
    """
    if args.from_file is not None:
        path = Path(args.from_file)
        if not path.exists():
            print(f"ERROR: --from-file path does not exist: {path}", file=sys.stderr)
            sys.exit(1)
        return path.read_text(encoding="utf-8")

    if args.body == "-":
        return sys.stdin.read()

    return args.body


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write verbatim content into the raw/ tier (Tier 0).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/ingest_raw.py --from-file notes.md --source "meeting 2026-06-15"
  python scripts/ingest_raw.py --body "some text" --source "pasted"
  echo "hello" | python scripts/ingest_raw.py --body - --source "stdin"
        """,
    )

    # Required
    parser.add_argument(
        "--source", required=True,
        help="Where the content came from (URL, file path, meeting name, etc.).",
    )

    # Content — exactly one must be provided (validated below)
    content_group = parser.add_mutually_exclusive_group(required=True)
    content_group.add_argument(
        "--from-file", metavar="PATH",
        help="Read verbatim body from this file path.",
    )
    content_group.add_argument(
        "--body", metavar="TEXT",
        help="Inline body text; use '-' to read from stdin.",
    )

    # Optional
    parser.add_argument(
        "--title", default="",
        help="Human-readable label (stored in frontmatter only, does not alter body).",
    )

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Ensure the raw/ directory exists.
    RAW_DIR.mkdir(parents=False, exist_ok=True)

    # Collision-safe id within raw/.
    raw_id = generate_id(RAW_DIR)

    # Today's date for the imported field.
    imported = date.today().strftime("%Y-%m-%d")

    # Resolve the body (verbatim — no reformatting).
    body = resolve_body(args)

    # Build frontmatter + body.  One blank line separates header from body.
    frontmatter = build_raw_frontmatter(
        raw_id=raw_id,
        source=args.source,
        title=args.title,
        imported=imported,
    )
    # Preserve body exactly — only ensure the file ends with a newline.
    content = frontmatter + "\n\n" + body
    if not content.endswith("\n"):
        content += "\n"

    # Write.
    output_path = RAW_DIR / f"{raw_id}.md"
    output_path.write_text(content, encoding="utf-8")

    # Report.
    print(f"id:   {raw_id}")
    print(f"path: {output_path}")


if __name__ == "__main__":
    main()
