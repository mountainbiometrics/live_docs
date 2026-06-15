#!/usr/bin/env python3
"""
new_doc.py — Create a new live_docs document.

Generates a timestamped, typed markdown doc in docs/<id>.md.
Uses stdlib only (argparse, datetime, pathlib). No external dependencies.

Usage:
    python scripts/new_doc.py --type decision --title "Use flat doc store"
    echo "Body text" | python scripts/new_doc.py --type principle --title "Keep it simple" --body -
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure scripts/ is on sys.path so livedocs is importable from any CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from livedocs import DOCS_DIR, generate_id


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"

# Types that require extra frontmatter fields beyond the canonical baseline.
REFERENCE_KIND_CHOICES = ("brainstorm", "plan", "clipping", "external")


# ---------------------------------------------------------------------------
# ISO 8601 timestamp for frontmatter fields
# ---------------------------------------------------------------------------

def now_iso() -> str:
    """Return the current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# YAML emission helpers (hand-rolled — no pyyaml)
# ---------------------------------------------------------------------------

def yaml_str(value: str) -> str:
    """Wrap a string value in quotes, escaping inner quotes."""
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def yaml_list(items: list) -> str:
    """Render a list inline, e.g. [live_docs, sinai]."""
    if not items:
        return "[]"
    inner = ", ".join(items)
    return f"[{inner}]"


def build_frontmatter(args, doc_id: str, created: str) -> str:
    """
    Construct the YAML frontmatter block as a string.
    Emits canonical baseline fields first, then type-specific extras.
    """
    depends_on_ids = [s.strip() for s in args.depends_on.split(",") if s.strip()] \
        if args.depends_on else []
    references_ids = [s.strip() for s in args.references.split(",") if s.strip()] \
        if args.references else []
    domain_tags = [s.strip() for s in args.tags_domain.split(",") if s.strip()] \
        if args.tags_domain else []
    scope_tags = [s.strip() for s in args.tags_scope.split(",") if s.strip()] \
        if args.tags_scope else []

    lines = [
        "---",
        f"id: {yaml_str(doc_id)}",
        f"title: {yaml_str(args.title)}",
        f"type: {args.type}",
        f"status: {args.status}",
        f"level: {args.level}",
        f"state: {args.state}",
        f"depends_on: {yaml_list(depends_on_ids)}",
        f"references: {yaml_list(references_ids)}",
        "tags:",
        f"  domain: {yaml_list(domain_tags)}",
        f"  scope: {yaml_list(scope_tags)}",
        f"created: {yaml_str(created)}",
        "history: []",
    ]

    # Reference-type extras
    if args.type == "reference":
        kind = args.kind or "clipping"
        source = args.source or ""
        lines.insert(lines.index("status: " + args.status),
                     f"kind: {kind}")
        lines.append(f"source: {yaml_str(source)}")
        lines.append(f"imported: {yaml_str(created)}")

    lines.append("---")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Template loading
# ---------------------------------------------------------------------------

def load_template_body(doc_type: str) -> str:
    """
    Return the body (non-frontmatter) portion of the template for doc_type,
    or an empty string if no template file exists.
    """
    template_path = TEMPLATES_DIR / f"{doc_type}.md"
    if not template_path.exists():
        return ""

    content = template_path.read_text(encoding="utf-8")
    # Strip the frontmatter block (everything between the first two '---' lines).
    parts = content.split("---", 2)
    if len(parts) >= 3:
        # parts[0] = "", parts[1] = frontmatter, parts[2] = body
        return parts[2].lstrip("\n")
    # No frontmatter in template — return whole content as body.
    return content.lstrip("\n")


# ---------------------------------------------------------------------------
# Body resolution
# ---------------------------------------------------------------------------

def resolve_body(args, doc_type: str) -> str:
    """
    Determine the document body:
    1. If --body - is given, read from stdin.
    2. If --body <text> is given, use that text.
    3. Otherwise fall back to the template body for the type.
    """
    if args.body == "-":
        return sys.stdin.read()
    if args.body:
        return args.body
    return load_template_body(doc_type)


# ---------------------------------------------------------------------------
# Document assembly
# ---------------------------------------------------------------------------

def assemble_document(frontmatter: str, body: str) -> str:
    """Combine frontmatter and body into the final file content."""
    body = body.strip()
    if body:
        return f"{frontmatter}\n\n{body}\n"
    return f"{frontmatter}\n"


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

VALID_TYPES = (
    "type", "principle", "goal", "decision", "constraint",
    "requirement", "use-case", "guide", "component", "reference", "index",
)
VALID_LEVELS = ("incidental", "trial", "preference", "requirement")
VALID_STATES = ("actual", "target")
VALID_STATUSES = ("living", "historical")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a new live_docs document in docs/<id>.md.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/new_doc.py --type decision --title "Use flat doc store"
  python scripts/new_doc.py --type principle --title "Prefer explicitness" --level preference
  python scripts/new_doc.py --type reference --kind clipping --source "https://..." --title "Prior art"
  echo "Body text here." | python scripts/new_doc.py --type goal --title "Ship Phase 1" --body -
        """,
    )

    # Required
    parser.add_argument("--type", required=True, choices=VALID_TYPES,
                        help="Document type (must be one of the 11 defined types).")
    parser.add_argument("--title", required=True,
                        help="Human-readable title (stored in frontmatter only).")

    # Optional with defaults
    parser.add_argument("--level", default="incidental", choices=VALID_LEVELS,
                        help="Adoption level (default: incidental).")
    parser.add_argument("--state", default="actual", choices=VALID_STATES,
                        help="Actual vs. target state (default: actual).")
    parser.add_argument("--status", default="living", choices=VALID_STATUSES,
                        help="Living or historical (default: living).")

    # Relationships & tags
    parser.add_argument("--depends-on", default="",
                        help="Comma-separated list of doc ids this doc structurally depends on (cascade graph).")
    parser.add_argument("--references", default="",
                        help="Comma-separated list of doc ids this doc is informed by / derived from (provenance only, NOT cascade edges).")
    parser.add_argument("--tags-domain", default="",
                        help="Comma-separated domain tags.")
    parser.add_argument("--tags-scope", default="",
                        help="Comma-separated scope tags (e.g. live_docs,sinai).")

    # Reference-type extras
    parser.add_argument("--kind", default="", choices=list(REFERENCE_KIND_CHOICES) + [""],
                        help="Reference subtype: brainstorm|plan|clipping|external.")
    parser.add_argument("--source", default="",
                        help="Where the reference came from (URL, person, meeting, etc.).")

    # Body
    parser.add_argument("--body", default="",
                        help="Document body text. Use '-' to read from stdin.")

    return parser


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Validate reference-specific rules
    if args.type == "reference" and args.kind == "":
        args.kind = "clipping"  # sensible default; spec says kind is required

    # Generate a collision-safe id (delegates to shared livedocs.generate_id)
    doc_id = generate_id(DOCS_DIR)
    created = now_iso()

    # Build document parts
    frontmatter = build_frontmatter(args, doc_id, created)
    body = resolve_body(args, args.type)
    document = assemble_document(frontmatter, body)

    # Write file
    output_path = DOCS_DIR / f"{doc_id}.md"
    output_path.write_text(document, encoding="utf-8")

    # Report
    print(f"id:   {doc_id}")
    print(f"path: {output_path}")


if __name__ == "__main__":
    main()
