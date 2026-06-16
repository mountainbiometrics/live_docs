#!/usr/bin/env python3
"""
ldoc.py — Unified porcelain CLI for the live_docs store.

Usage:
    ldoc <subcommand> [args...]

All ref arguments accept: id | label | title (exact or unique substring).
Stdlib only. No external dependencies.

Subcommands:
    get <ref> [--json]
    body <ref>
    show <ref> [--json]
    find [query] [--type] [--level] [--state] [--status] [--scope] [--domain] [--json]
    ls [--type] [--json]
    resolve <ref>
    label <ref>
    neighbors <ref> [--kind depends_on|references|dependents|referenced_by|all] [--json]
    graph <ref> [--depth N] [--direction up|down|both] [--json]
    new --type T --title T [--label L] [--level L] [--state S] [--status S]
        [--depends-on a,b] [--references c,d] [--tags-domain d] [--tags-scope s]
        [--kind K] [--source S] [--body T|-]
    set <ref> [--title] [--label] [--level] [--state] [--status] [--type]
    link <ref> [--depends-on a,b] [--references c,d]
    unlink <ref> [--depends-on a,b] [--references c,d]
    history <ref> --add "summary"
    ingest-raw (--from-file P | --body T|-) --source S [--title T] [--label L]
    validate
    reindex
    edges [--json]
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure scripts/ is on sys.path so livedocs is importable from any CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from livedocs import KB, DOCS_DIR, LABEL_RE, VALID_TYPES, VALID_LEVELS, VALID_STATES, VALID_STATUSES, VALID_REFERENCE_KINDS
from livedocs import ReviewLedger, REVIEWS_DIR


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _fmt_edge_list(edges: list[dict]) -> str:
    """Format [{id, label, display}] for human display (always carries the label)."""
    if not edges:
        return "  (none)"
    lines = []
    for e in edges:
        label_part = f" [{e['label']}]" if e.get("label") else ""
        lines.append(f"  {e['id']}{label_part}  {e.get('display', '')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_get(kb: KB, args) -> int:
    try:
        result = kb.get(args.ref)
    except ValueError as e:
        _err(str(e))
        return 1

    if args.json:
        _json(result)
        return 0

    fm = result["frontmatter"]
    print(f"id:     {result['id']}")
    print(f"label:  {result['label']}")
    print(f"title:  {result['display']}")
    print(f"type:   {fm.get('type', '')}")
    print(f"status: {fm.get('status', '')}  level: {fm.get('level', '')}  state: {fm.get('state', '')}")
    print(f"created: {fm.get('created', '')}")
    tags = fm.get("tags", {})
    print(f"tags:   domain={tags.get('domain',[])}  scope={tags.get('scope',[])}")
    hist = fm.get("history", [])
    print(f"history: {len(hist)} entries")
    return 0


def cmd_body(kb: KB, args) -> int:
    try:
        text = kb.body(args.ref)
    except ValueError as e:
        _err(str(e))
        return 1
    print(text, end="")
    return 0


def cmd_show(kb: KB, args) -> int:
    try:
        result = kb.show(args.ref)
    except ValueError as e:
        _err(str(e))
        return 1

    if args.json:
        _json(result)
        return 0

    fm = result["frontmatter"]
    print(f"{'='*60}")
    print(f"  {result['display']}")
    print(f"  id:     {result['id']}")
    print(f"  label:  {result['label']}")
    print(f"  type:   {fm.get('type','')}  status: {fm.get('status','')}  "
          f"level: {fm.get('level','')}  state: {fm.get('state','')}")
    tags = fm.get("tags", {})
    print(f"  tags:   domain={tags.get('domain',[])}  scope={tags.get('scope',[])}")
    print(f"  created: {fm.get('created','')}")
    print(f"{'='*60}")
    print()

    print("DEPENDS ON:")
    print(_fmt_edge_list(result["depends_on"]))
    print()
    print("REFERENCES:")
    print(_fmt_edge_list(result["references"]))
    print()
    print("DEPENDENTS:")
    print(_fmt_edge_list(result["dependents"]))
    print()
    print("REFERENCED BY:")
    print(_fmt_edge_list(result["referenced_by"]))
    print()

    hist = fm.get("history", [])
    if hist:
        print("HISTORY:")
        for h in hist:
            print(f"  {h.get('at','')}  {h.get('summary','')}")
        print()

    body = result.get("body", "").strip()
    if body:
        print("BODY:")
        print(body)

    return 0


def cmd_find(kb: KB, args) -> int:
    try:
        results = kb.find(
            query=args.query or None,
            type=args.type or None,
            level=args.level or None,
            state=args.state or None,
            status=args.status or None,
            scope=args.scope or None,
            domain=args.domain or None,
        )
    except Exception as e:
        _err(str(e))
        return 1

    if args.json:
        _json(results)
        return 0

    if not results:
        print("(no results)")
        return 0

    for r in results:
        label_part = f" [{r['label']}]" if r.get("label") else ""
        print(f"{r['id']}{label_part}  {r.get('display', '')}")
        if r.get("snippet"):
            print(f"  {r['snippet']}")

    return 0


def cmd_ls(kb: KB, args) -> int:
    try:
        results = kb.ls(type=args.type or None)
    except Exception as e:
        _err(str(e))
        return 1

    if args.json:
        _json(results)
        return 0

    for r in results:
        label_part = f" [{r['label']}]" if r.get("label") else ""
        print(f"{r['id']}{label_part}  {r.get('display', '')}")

    return 0


def cmd_resolve(kb: KB, args) -> int:
    try:
        doc_id = kb.resolve(args.ref)
    except ValueError as e:
        _err(str(e))
        return 1
    print(doc_id)
    return 0


def cmd_label(kb: KB, args) -> int:
    try:
        doc_id = kb.resolve(args.ref)
        print(kb.display_label(doc_id))
    except ValueError as e:
        _err(str(e))
        return 1
    return 0


def cmd_neighbors(kb: KB, args) -> int:
    try:
        result = kb.neighbors(args.ref, kind=args.kind)
    except ValueError as e:
        _err(str(e))
        return 1

    if args.json:
        _json(result)
        return 0

    for edge_kind, edges in result.items():
        print(f"{edge_kind.upper()}:")
        print(_fmt_edge_list(edges))
        print()

    return 0


def cmd_graph(kb: KB, args) -> int:
    try:
        result = kb.graph(args.ref, depth=args.depth, direction=args.direction)
    except ValueError as e:
        _err(str(e))
        return 1

    if args.json:
        _json(result)
        return 0

    print(f"Graph from {args.ref!r}  (depth={args.depth}, direction={args.direction})")
    print()
    print("NODES:")
    for n in result["nodes"]:
        label_part = f" [{n['label']}]" if n.get("label") else ""
        print(f"  depth={n['depth']}  {n['id']}{label_part}  {n.get('display', '')}")
    print()
    print("EDGES (from → to):")
    for edge in result["edges"]:
        print(f"  {edge[0]} → {edge[1]}")

    return 0


def cmd_new(kb: KB, args) -> int:
    # Resolve depends_on / references
    depends_on_refs = [s.strip() for s in args.depends_on.split(",") if s.strip()] \
        if args.depends_on else []
    references_refs = [s.strip() for s in args.references.split(",") if s.strip()] \
        if args.references else []
    domain_tags = [s.strip() for s in args.tags_domain.split(",") if s.strip()] \
        if args.tags_domain else []
    scope_tags = [s.strip() for s in args.tags_scope.split(",") if s.strip()] \
        if args.tags_scope else []

    # Resolve edge refs
    try:
        dep_ids = [kb.resolve(r) for r in depends_on_refs] if depends_on_refs else []
        ref_ids = [kb.resolve(r) for r in references_refs] if references_refs else []
    except ValueError as e:
        _err(str(e))
        return 1

    # Body
    if args.body == "-":
        body = sys.stdin.read()
    elif args.body:
        body = args.body
    else:
        body = ""

    try:
        doc_id = kb.new(
            type=args.type,
            title=args.title,
            label=args.label or "",
            level=args.level,
            state=args.state,
            status=args.status,
            depends_on=dep_ids,
            references=ref_ids,
            tags_domain=domain_tags,
            tags_scope=scope_tags,
            body=body,
            kind=args.kind or "",
            source=args.source or "",
        )
    except Exception as e:
        _err(str(e))
        return 1

    print(f"id:   {doc_id}")
    print(f"path: {kb.docs_dir / doc_id}.md")
    return 0


def cmd_set(kb: KB, args) -> int:
    fields = {}
    if args.title is not None:
        fields["title"] = args.title
    if args.label is not None:
        label = args.label.strip()
        if not LABEL_RE.match(label):
            _err(f"Invalid label: {args.label!r}. Must match "
                 f"^[A-Za-z0-9]+([ -][A-Za-z0-9]+)*$ (letters/digits, single spaces or hyphens).")
            return 1
        fields["label"] = label
    if args.level is not None:
        fields["level"] = args.level
    if args.state is not None:
        fields["state"] = args.state
    if args.status is not None:
        fields["status"] = args.status
    if args.type is not None:
        fields["type"] = args.type

    if not fields:
        _err("No fields specified. Use --title, --label, --level, --state, --status, --type.")
        return 1

    try:
        kb.set(args.ref, **fields)
    except ValueError as e:
        _err(str(e))
        return 1

    print(f"Updated {args.ref}")
    return 0


def cmd_link(kb: KB, args) -> int:
    depends_on_refs = [s.strip() for s in args.depends_on.split(",") if s.strip()] \
        if args.depends_on else []
    references_refs = [s.strip() for s in args.references.split(",") if s.strip()] \
        if args.references else []

    if not depends_on_refs and not references_refs:
        _err("Specify --depends-on or --references (or both).")
        return 1

    try:
        kb.link(args.ref, depends_on=depends_on_refs or None, references=references_refs or None)
    except ValueError as e:
        _err(str(e))
        return 1

    print(f"Linked {args.ref}")
    return 0


def cmd_unlink(kb: KB, args) -> int:
    depends_on_refs = [s.strip() for s in args.depends_on.split(",") if s.strip()] \
        if args.depends_on else []
    references_refs = [s.strip() for s in args.references.split(",") if s.strip()] \
        if args.references else []

    if not depends_on_refs and not references_refs:
        _err("Specify --depends-on or --references (or both).")
        return 1

    try:
        kb.unlink(args.ref, depends_on=depends_on_refs or None, references=references_refs or None)
    except ValueError as e:
        _err(str(e))
        return 1

    print(f"Unlinked {args.ref}")
    return 0


def cmd_history(kb: KB, args) -> int:
    if not args.add:
        _err("Specify --add 'summary text'.")
        return 1

    try:
        kb.add_history(args.ref, args.add)
    except ValueError as e:
        _err(str(e))
        return 1

    print(f"History entry added to {args.ref}")
    return 0


def cmd_ingest_raw(kb: KB, args) -> int:
    body = ""
    from_file = ""

    if args.from_file:
        from_file = args.from_file
    elif args.body == "-":
        body = sys.stdin.read()
    elif args.body:
        body = args.body
    else:
        _err("Provide --from-file or --body.")
        return 1

    try:
        raw_id = kb.ingest_raw(
            source=args.source,
            body=body,
            from_file=from_file,
            title=args.title or "",
            label=args.label or "",
        )
    except Exception as e:
        _err(str(e))
        return 1

    from livedocs import RAW_DIR
    print(f"id:   {raw_id}")
    print(f"path: {RAW_DIR / raw_id}.md")
    return 0


def cmd_validate(kb: KB, args) -> int:
    """Delegate to validate logic (same as validate.py) via shared KB state."""
    import subprocess
    script = Path(__file__).resolve().parent / "validate.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=False)
    return result.returncode


def cmd_reindex(kb: KB, args) -> int:
    """Delegate to reindex logic via reindex.py."""
    import subprocess
    script = Path(__file__).resolve().parent / "reindex.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=False)
    return result.returncode


def cmd_review(kb: KB, args) -> int:
    """Dispatch ldoc review <subverb> commands over the reviews/ ledger."""
    ledger = ReviewLedger(reviews_dir=REVIEWS_DIR, docs_dir=kb.docs_dir)
    verb = args.review_verb

    if verb == "new":
        return _review_new(ledger, args)
    elif verb == "list":
        return _review_list(ledger, args)
    elif verb == "show":
        return _review_show(ledger, args)
    elif verb == "sign":
        return _review_sign(ledger, args)
    else:
        _err(f"Unknown review subcommand: {verb!r}")
        return 1


def _review_new(ledger: ReviewLedger, args) -> int:
    since = args.since or ""
    touched_refs = None
    body = ""

    if args.touched:
        touched_refs = [r.strip() for r in args.touched.split(",") if r.strip()]

    if args.summary == "-":
        body = sys.stdin.read()
    elif args.summary:
        body = args.summary

    if not since and touched_refs is None and not body:
        _err("Provide --since <ISO8601>, --touched <refs>, or --summary <text|->, or a combination.")
        return 1

    try:
        review_id, path = ledger.new(since=since, touched_refs=touched_refs, body=body)
    except Exception as e:
        _err(str(e))
        return 1

    print(f"id:   {review_id}")
    print(f"path: {path}")
    return 0


def _review_list(ledger: ReviewLedger, args) -> int:
    unsigned_by = args.unsigned_by or ""
    try:
        records = ledger.list_reviews(unsigned_by=unsigned_by)
    except Exception as e:
        _err(str(e))
        return 1

    if not records:
        print("(no review records)")
        return 0

    for r in records:
        signer_str = ", ".join(r["signers"]) if r["signers"] else "(unsigned)"
        print(f"{r['id']}  created={r['created']}  touched={r['touched_count']}  signers=[{signer_str}]")

    return 0


def _review_show(ledger: ReviewLedger, args) -> int:
    try:
        rec = ledger.show(args.ref)
    except ValueError as e:
        _err(str(e))
        return 1

    print(f"{'='*60}")
    print(f"  Review: {rec['id']}")
    print(f"  created:  {rec.get('created', '')}")
    print(f"  touched:  {len(rec.get('touched', []))} docs  {rec.get('touched', [])}")
    print(f"{'='*60}")
    print()

    signoffs = rec.get("signoffs", [])
    if signoffs:
        print("SIGNOFFS:")
        for s in signoffs:
            print(f"  {s.get('at', '')}  {s.get('who', '')}")
        print()
    else:
        print("SIGNOFFS: (none)")
        print()

    body = rec.get("body", "").strip()
    if body:
        print("SUMMARY:")
        print(body)

    return 0


def _review_sign(ledger: ReviewLedger, args) -> int:
    if not args.as_who:
        _err("--as <who> is required.")
        return 1

    try:
        at = ledger.sign(args.ref, args.as_who)
    except ValueError as e:
        _err(str(e))
        return 1

    print(f"Signed {args.ref!r} as {args.as_who!r} at {at}")
    return 0


def cmd_edges(kb: KB, args) -> int:
    """Delegate to edges.py."""
    import subprocess
    script = Path(__file__).resolve().parent / "edges.py"
    cmd = [sys.executable, str(script)]
    if args.json:
        cmd.append("--json")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

VALID_TYPES = sorted(VALID_TYPES)
VALID_LEVELS = sorted(VALID_LEVELS)
VALID_STATES = sorted(VALID_STATES)
VALID_STATUSES = sorted(VALID_STATUSES)
REFERENCE_KIND_CHOICES = sorted(VALID_REFERENCE_KINDS) + [""]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ldoc",
        description="live_docs porcelain CLI — query and mutate the KB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="subcommand", metavar="subcommand")
    sub.required = True

    # --- get ---
    p = sub.add_parser("get", help="Show frontmatter summary for a doc.")
    p.add_argument("ref", help="id | label | title")
    p.add_argument("--json", action="store_true")

    # --- body ---
    p = sub.add_parser("body", help="Print the body text of a doc.")
    p.add_argument("ref", help="id | label | title")

    # --- show ---
    p = sub.add_parser("show", help="Show full doc with resolved edge labels.")
    p.add_argument("ref", help="id | label | title")
    p.add_argument("--json", action="store_true")

    # --- find ---
    p = sub.add_parser("find", help="Search/filter docs.")
    p.add_argument("query", nargs="?", default="", help="Optional query string (searches title+label+body).")
    p.add_argument("--type", default="")
    p.add_argument("--level", default="")
    p.add_argument("--state", default="")
    p.add_argument("--status", default="")
    p.add_argument("--scope", default="")
    p.add_argument("--domain", default="")
    p.add_argument("--json", action="store_true")

    # --- ls ---
    p = sub.add_parser("ls", help="List all docs (optionally filter by type).")
    p.add_argument("--type", default="")
    p.add_argument("--json", action="store_true")

    # --- resolve ---
    p = sub.add_parser("resolve", help="Resolve a ref to its canonical id.")
    p.add_argument("ref", help="id | label | title")

    # --- label ---
    p = sub.add_parser("label", help="Print '<Type>: <Title>' label for a ref.")
    p.add_argument("ref", help="id | label | title")

    # --- neighbors ---
    p = sub.add_parser("neighbors", help="Show neighbors of a doc.")
    p.add_argument("ref", help="id | label | title")
    p.add_argument("--kind", default="all",
                   choices=["depends_on", "references", "dependents", "referenced_by", "all"])
    p.add_argument("--json", action="store_true")

    # --- graph ---
    p = sub.add_parser("graph", help="BFS traversal over depends_on edges.")
    p.add_argument("ref", help="id | label | title")
    p.add_argument("--depth", type=int, default=1)
    p.add_argument("--direction", default="both", choices=["up", "down", "both"])
    p.add_argument("--json", action="store_true")

    # --- new ---
    p = sub.add_parser("new", help="Create a new doc.")
    p.add_argument("--type", required=True, choices=VALID_TYPES)
    p.add_argument("--title", required=True)
    p.add_argument("--label", default="",
                   help="Short label; auto-derived from title (word-boundary) if omitted.")
    p.add_argument("--level", default="incidental", choices=VALID_LEVELS)
    p.add_argument("--state", default="actual", choices=VALID_STATES)
    p.add_argument("--status", default="living", choices=VALID_STATUSES)
    p.add_argument("--depends-on", default="", dest="depends_on",
                   help="Comma-separated ids/labels/titles.")
    p.add_argument("--references", default="",
                   help="Comma-separated ids/labels/titles.")
    p.add_argument("--tags-domain", default="", dest="tags_domain")
    p.add_argument("--tags-scope", default="", dest="tags_scope")
    p.add_argument("--kind", default="", choices=REFERENCE_KIND_CHOICES + [""])
    p.add_argument("--source", default="")
    p.add_argument("--body", default="", help="Body text or '-' to read from stdin.")

    # --- set ---
    p = sub.add_parser("set", help="Update scalar frontmatter fields.")
    p.add_argument("ref", help="id | label | title")
    p.add_argument("--title", default=None)
    p.add_argument("--label", default=None)
    p.add_argument("--level", default=None, choices=VALID_LEVELS)
    p.add_argument("--state", default=None, choices=VALID_STATES)
    p.add_argument("--status", default=None, choices=VALID_STATUSES)
    p.add_argument("--type", default=None, choices=VALID_TYPES)

    # --- link ---
    p = sub.add_parser("link", help="Add edge(s) to a doc.")
    p.add_argument("ref", help="id | label | title")
    p.add_argument("--depends-on", default="", dest="depends_on",
                   help="Comma-separated ids/labels/titles.")
    p.add_argument("--references", default="",
                   help="Comma-separated ids/labels/titles.")

    # --- unlink ---
    p = sub.add_parser("unlink", help="Remove edge(s) from a doc.")
    p.add_argument("ref", help="id | label | title")
    p.add_argument("--depends-on", default="", dest="depends_on",
                   help="Comma-separated ids/labels/titles.")
    p.add_argument("--references", default="",
                   help="Comma-separated ids/labels/titles.")

    # --- history ---
    p = sub.add_parser("history", help="Add a history entry to a doc.")
    p.add_argument("ref", help="id | label | title")
    p.add_argument("--add", required=True, help="Summary text for the history entry.")

    # --- ingest-raw ---
    p = sub.add_parser("ingest-raw", help="Write verbatim content into raw/ tier.")
    p.add_argument("--source", required=True)
    p.add_argument("--from-file", default="", dest="from_file")
    p.add_argument("--body", default="")
    p.add_argument("--title", default="")
    p.add_argument("--label", default="")

    # --- validate ---
    p = sub.add_parser("validate", help="Run structural integrity checks.")
    # no extra args

    # --- reindex ---
    p = sub.add_parser("reindex", help="Rebuild docs/.index/ artifacts.")
    # no extra args

    # --- edges ---
    p = sub.add_parser("edges", help="Print forward/reverse edge maps.")
    p.add_argument("--json", action="store_true")

    # --- review ---
    p_rev = sub.add_parser("review", help="Manage review summaries in the reviews/ ledger.")
    rev_sub = p_rev.add_subparsers(dest="review_verb", metavar="verb")
    rev_sub.required = True

    # review new
    p_rn = rev_sub.add_parser("new", help="Create a new review summary record.")
    p_rn.add_argument("--since", default="",
                      help="ISO 8601 UTC timestamp; scan docs/ for changes since this time.")
    p_rn.add_argument("--touched", default="",
                      help="Comma-separated doc ids/refs to include explicitly.")
    p_rn.add_argument("--summary", default="",
                      help="Summary body text, or '-' to read from stdin.")

    # review list
    p_rl = rev_sub.add_parser("list", help="List review records.")
    p_rl.add_argument("--unsigned-by", default="", dest="unsigned_by",
                      help="Show only records NOT signed by this name.")

    # review show
    p_rs = rev_sub.add_parser("show", help="Show a review record.")
    p_rs.add_argument("ref", help="Review record id (or unique prefix/substring).")

    # review sign
    p_rsg = rev_sub.add_parser("sign", help="Sign a review record.")
    p_rsg.add_argument("ref", help="Review record id (or unique prefix/substring).")
    p_rsg.add_argument("--as", dest="as_who", required=True,
                       help="Your name (free-text signature).")

    return parser


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

COMMANDS = {
    "get": cmd_get,
    "body": cmd_body,
    "show": cmd_show,
    "find": cmd_find,
    "ls": cmd_ls,
    "resolve": cmd_resolve,
    "label": cmd_label,
    "neighbors": cmd_neighbors,
    "graph": cmd_graph,
    "new": cmd_new,
    "set": cmd_set,
    "link": cmd_link,
    "unlink": cmd_unlink,
    "history": cmd_history,
    "ingest-raw": cmd_ingest_raw,
    "validate": cmd_validate,
    "reindex": cmd_reindex,
    "edges": cmd_edges,
    "review": cmd_review,
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    kb = KB(DOCS_DIR)

    handler = COMMANDS.get(args.subcommand)
    if not handler:
        _err(f"Unknown subcommand: {args.subcommand}")
        return 1

    return handler(kb, args)


if __name__ == "__main__":
    sys.exit(main())
