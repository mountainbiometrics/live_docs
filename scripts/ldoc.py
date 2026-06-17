#!/usr/bin/env python3
"""
ldoc.py — Unified porcelain CLI for the live_docs store.

Usage:
    ldoc <subcommand> [args...]

All ref arguments accept: id | label | title (exact or unique substring).
Multiple refs: most read verbs accept one or more refs (space-separated).
  Pass - as the sole ref to read refs from stdin (one per line).
Stdlib only. No external dependencies.

Subcommands (grouped):
  ── Reads ──
    get <ref> [<ref2> ...]  [--json]
    body <ref> [<ref2> ...]
    show <ref> [<ref2> ...]  [--json] [--plain]
    resolve <ref> [<ref2> ...]
    label <ref> [<ref2> ...]
    neighbors <ref> [<ref2> ...]  [--kind depends_on|references|dependents|referenced_by|all] [--json]

  ── Search / list ──
    find [term ...] [--or] [--regex PAT]
         [--type] [--level] [--state] [--status] [--scope] [--domain] [--json] [--plain]
    ls [--type] [--json] [--plain]
    log [--since <ISO>] [--limit N] [--json]
    count [--json]

  ── Graph ──
    graph <ref> [--depth N] [--direction up|down|both] [--json]
    edges [--json]

  ── Mutations ──
    new --type T --title T [--label L] [--level L] [--state S] [--status S]
        [--depends-on a,b] [--references c,d] [--tags-domain d] [--tags-scope s]
        [--kind K] [--source S] [--body T|-] [--dry-run]
    set <ref> [--title] [--label] [--level] [--state] [--status] [--type]
              [--body -|TEXT] [--dry-run]
    edit <ref>   (alias: set <ref> --body -)
    link <ref> [--depends-on a,b] [--references c,d] [--dry-run]
    unlink <ref> [--depends-on a,b] [--references c,d]
    history <ref> --add "summary"
    ingest-raw (--from-file P | --body T|-) --source S [--title T] [--label L]

  ── Maintenance ──
    validate
    reindex
    review <new|list|show|sign> ...

  ── Help ──
    help
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure scripts/ is on sys.path so livedocs is importable from any CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from livedocs import KB, DOCS_DIR, LABEL_RE, VALID_TYPES, VALID_LEVELS, VALID_STATES, VALID_STATUSES, VALID_REFERENCE_KINDS
from livedocs import ReviewLedger, REVIEWS_DIR
from livedocs.model import ref_link


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _fmt_edge_list(edges: list[dict], plain: bool = False) -> str:
    """
    Format [{id, label, display}] for human display.

    plain=False (default): typed wiki-link format '[<Type>: <Title>](<id>.md)'
    plain=True: '<id> [<label>] <Type>: <Title>'
    """
    if not edges:
        return "  (none)"
    lines = []
    for e in edges:
        if plain:
            label_part = f" [{e['label']}]" if e.get("label") else ""
            lines.append(f"  {e['id']}{label_part}  {e.get('display', '')}")
        else:
            doc_id = e["id"]
            display = e.get("display", "")
            lines.append(f"  [{display}]({doc_id}.md)")
    return "\n".join(lines)


def _resolve_refs(kb: KB, raw_refs: list[str]) -> list[str] | None:
    """
    Resolve a list of raw ref strings (possibly containing '-' for stdin).

    Returns the list of resolved refs, or None on error (already printed).
    '-' as the only element means read refs from stdin (one per line).
    """
    if raw_refs == ["-"]:
        stdin_refs = [line.strip() for line in sys.stdin if line.strip()]
        return stdin_refs
    return list(raw_refs)


# ---------------------------------------------------------------------------
# Batch helpers — wrap single-ref KB calls into multi-ref loops
# ---------------------------------------------------------------------------

_BATCH_SEP = "---"


def _batch_output(items: list, render_fn, sep: str = _BATCH_SEP) -> int:
    """
    Render a list of items via render_fn(item) -> None.
    Separate multiple items with sep. Returns 0 on success.
    """
    for i, item in enumerate(items):
        if i > 0:
            print(sep)
        render_fn(item)
    return 0


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_get(kb: KB, args) -> int:
    refs = _resolve_refs(kb, args.refs)
    if refs is None:
        return 1

    def render(ref: str) -> None:
        try:
            result = kb.get(ref)
        except ValueError as e:
            _err(str(e))
            return

        if args.json:
            print(json.dumps(result, indent=2, default=str))
            return

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

    if args.json and len(refs) > 1:
        results = []
        for ref in refs:
            try:
                results.append(kb.get(ref))
            except ValueError as e:
                _err(str(e))
                return 1
        _json(results)
        return 0

    return _batch_output(refs, render)


def cmd_body(kb: KB, args) -> int:
    refs = _resolve_refs(kb, args.refs)
    if refs is None:
        return 1

    for i, ref in enumerate(refs):
        if i > 0:
            print(_BATCH_SEP)
        try:
            text = kb.body(ref)
        except ValueError as e:
            _err(str(e))
            return 1
        print(text, end="")

    return 0


def cmd_show(kb: KB, args) -> int:
    refs = _resolve_refs(kb, args.refs)
    if refs is None:
        return 1

    plain = getattr(args, "plain", False)

    if args.json and len(refs) > 1:
        results = []
        for ref in refs:
            try:
                results.append(kb.show(ref))
            except ValueError as e:
                _err(str(e))
                return 1
        _json(results)
        return 0

    def render(ref: str) -> None:
        try:
            result = kb.show(ref)
        except ValueError as e:
            _err(str(e))
            return

        if args.json:
            print(json.dumps(result, indent=2, default=str))
            return

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
        print(_fmt_edge_list(result["depends_on"], plain=plain))
        print()
        print("REFERENCES:")
        print(_fmt_edge_list(result["references"], plain=plain))
        print()
        print("DEPENDENTS:")
        print(_fmt_edge_list(result["dependents"], plain=plain))
        print()
        print("REFERENCED BY:")
        print(_fmt_edge_list(result["referenced_by"], plain=plain))
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

    return _batch_output(refs, render)


def cmd_find(kb: KB, args) -> int:
    # terms is nargs='*', may be empty list
    terms = args.terms or []
    plain = getattr(args, "plain", False)

    try:
        results = kb.find(
            terms=terms if terms else None,
            or_mode=getattr(args, "or_mode", False),
            regex=getattr(args, "regex", None) or None,
            type=args.type or None,
            level=args.level or None,
            state=args.state or None,
            status=args.status or None,
            scope=args.scope or None,
            domain=args.domain or None,
        )
    except ValueError as e:
        _err(str(e))
        return 1

    if args.json:
        _json(results)
        return 0

    if not results:
        print("(no results)")
        return 0

    for r in results:
        if plain:
            label_part = f" [{r['label']}]" if r.get("label") else ""
            print(f"{r['id']}{label_part}  {r.get('display', '')}")
        else:
            doc_id = r["id"]
            display = r.get("display", "")
            print(f"[{display}]({doc_id}.md)")
        if r.get("snippet"):
            print(f"  {r['snippet']}")

    return 0


def cmd_ls(kb: KB, args) -> int:
    plain = getattr(args, "plain", False)
    try:
        results = kb.ls(type=args.type or None)
    except Exception as e:
        _err(str(e))
        return 1

    if args.json:
        _json(results)
        return 0

    for r in results:
        if plain:
            label_part = f" [{r['label']}]" if r.get("label") else ""
            print(f"{r['id']}{label_part}  {r.get('display', '')}")
        else:
            doc_id = r["id"]
            display = r.get("display", "")
            print(f"[{display}]({doc_id}.md)")

    return 0


def cmd_resolve(kb: KB, args) -> int:
    refs = _resolve_refs(kb, args.refs)
    if refs is None:
        return 1

    for ref in refs:
        try:
            doc_id = kb.resolve(ref)
        except ValueError as e:
            _err(str(e))
            return 1
        print(doc_id)

    return 0


def cmd_label(kb: KB, args) -> int:
    refs = _resolve_refs(kb, args.refs)
    if refs is None:
        return 1

    for ref in refs:
        try:
            doc_id = kb.resolve(ref)
            print(kb.display_label(doc_id))
        except ValueError as e:
            _err(str(e))
            return 1

    return 0


def cmd_neighbors(kb: KB, args) -> int:
    refs = _resolve_refs(kb, args.refs)
    if refs is None:
        return 1

    plain = getattr(args, "plain", False)

    if args.json and len(refs) > 1:
        all_results = []
        for ref in refs:
            try:
                all_results.append({"ref": ref, **kb.neighbors(ref, kind=args.kind)})
            except ValueError as e:
                _err(str(e))
                return 1
        _json(all_results)
        return 0

    def render(ref: str) -> None:
        try:
            result = kb.neighbors(ref, kind=args.kind)
        except ValueError as e:
            _err(str(e))
            return

        if args.json:
            print(json.dumps(result, indent=2, default=str))
            return

        if len(refs) > 1:
            print(f"# {ref}")
        for edge_kind, edges in result.items():
            print(f"{edge_kind.upper()}:")
            print(_fmt_edge_list(edges, plain=plain))
            print()

    return _batch_output(refs, render)


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


def cmd_log(kb: KB, args) -> int:
    """Read-only recent-changes view. Does NOT create a review record."""
    since = getattr(args, "since", None) or None
    limit = getattr(args, "limit", None)

    try:
        events = kb.log(since=since, limit=limit)
    except Exception as e:
        _err(str(e))
        return 1

    if args.json:
        _json(events)
        return 0

    if not events:
        print("(no recent changes)")
        return 0

    for ev in events:
        doc_id = ev["id"]
        display = ev.get("display", "")
        at = ev.get("at", "")
        event = ev.get("event", "")
        summary = ev.get("summary", "")

        link = f"[{display}]({doc_id}.md)"
        if summary:
            print(f"{at}  {event}  {link} — {summary}")
        else:
            print(f"{at}  {event}  {link}")

    return 0


def cmd_count(kb: KB, args) -> int:
    """Doc and edge count statistics."""
    try:
        stats = kb.count()
    except Exception as e:
        _err(str(e))
        return 1

    if args.json:
        _json(stats)
        return 0

    print(f"Total docs: {stats['total']}")
    print()
    print("By type:")
    for k, v in stats["by_type"].items():
        print(f"  {k:20s}  {v}")
    print()
    print("By level:")
    for k, v in stats["by_level"].items():
        print(f"  {k:20s}  {v}")
    print()
    print("By state:")
    for k, v in stats["by_state"].items():
        print(f"  {k:20s}  {v}")
    print()
    print("By status:")
    for k, v in stats["by_status"].items():
        print(f"  {k:20s}  {v}")
    print()
    print(f"depends_on edges: {stats['edge_count']}")
    print(f"references edges: {stats['reference_count']}")

    return 0


def cmd_new(kb: KB, args) -> int:
    # Parse edge refs
    depends_on_refs = [s.strip() for s in args.depends_on.split(",") if s.strip()] \
        if args.depends_on else []
    references_refs = [s.strip() for s in args.references.split(",") if s.strip()] \
        if args.references else []
    domain_tags = [s.strip() for s in args.tags_domain.split(",") if s.strip()] \
        if args.tags_domain else []
    scope_tags = [s.strip() for s in args.tags_scope.split(",") if s.strip()] \
        if args.tags_scope else []

    # Edge-ref validation (capability 6): validate before writing
    if depends_on_refs or references_refs:
        unresolved = kb.validate_edge_refs(depends_on_refs, references_refs)
        if unresolved:
            _err(
                f"Unresolved edge ref(s): {', '.join(repr(r) for r in unresolved)}. "
                f"Check with: ldoc resolve <ref>"
            )
            return 1

    # Resolve edge refs to ids
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

    # --dry-run preview (capability 11)
    if getattr(args, "dry_run", False):
        from livedocs.model import title_to_label, unique_label
        label = args.label or ""
        if not label:
            existing = (d.get("label", "") for d in kb._docs.values())
            label = unique_label(title_to_label(args.title), existing)
        print("## DRY RUN — would create:\n")
        print(f"  type:    {args.type}")
        print(f"  title:   {args.title}")
        print(f"  label:   {label}")
        print(f"  level:   {args.level}")
        print(f"  state:   {args.state}")
        print(f"  status:  {args.status}")
        if dep_ids:
            print(f"  depends_on: {dep_ids}")
        if ref_ids:
            print(f"  references: {ref_ids}")
        if body.strip():
            print(f"\n  body preview:\n    {body.strip()[:200]}")
        print("\n(No doc written.)")
        return 0

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

    # --body: read new body from stdin or inline
    body_arg = getattr(args, "body", None)
    new_body = None
    if body_arg == "-":
        new_body = sys.stdin.read()
    elif body_arg:
        new_body = body_arg

    if not fields and new_body is None:
        _err("No fields specified. Use --title, --label, --level, --state, --status, --type, or --body.")
        return 1

    # --dry-run preview
    if getattr(args, "dry_run", False):
        print("## DRY RUN — would update:\n")
        try:
            doc_id = kb.resolve(args.ref)
        except ValueError as e:
            _err(str(e))
            return 1
        print(f"  doc: {doc_id}")
        for k, v in fields.items():
            print(f"  {k}: {v!r}")
        if new_body is not None:
            print(f"  body: (replace, {len(new_body)} chars)")
        print("\n(No doc written.)")
        return 0

    if fields:
        try:
            kb.set(args.ref, **fields)
        except ValueError as e:
            _err(str(e))
            return 1

    if new_body is not None:
        try:
            kb.set_body(args.ref, new_body)
        except ValueError as e:
            _err(str(e))
            return 1

    print(f"Updated {args.ref}")
    return 0


def cmd_edit(kb: KB, args) -> int:
    """Alias: read new body from stdin and replace doc body."""
    body = sys.stdin.read()
    try:
        kb.set_body(args.ref, body)
    except ValueError as e:
        _err(str(e))
        return 1
    print(f"Body updated for {args.ref}")
    return 0


def cmd_link(kb: KB, args) -> int:
    depends_on_refs = [s.strip() for s in args.depends_on.split(",") if s.strip()] \
        if args.depends_on else []
    references_refs = [s.strip() for s in args.references.split(",") if s.strip()] \
        if args.references else []

    if not depends_on_refs and not references_refs:
        _err("Specify --depends-on or --references (or both).")
        return 1

    # Edge-ref validation (capability 6)
    unresolved = kb.validate_edge_refs(depends_on_refs, references_refs)
    if unresolved:
        _err(
            f"Unresolved edge ref(s): {', '.join(repr(r) for r in unresolved)}. "
            f"Check with: ldoc resolve <ref>"
        )
        return 1

    # --dry-run preview
    if getattr(args, "dry_run", False):
        print("## DRY RUN — would link:\n")
        if depends_on_refs:
            print(f"  --depends-on: {depends_on_refs}")
        if references_refs:
            print(f"  --references: {references_refs}")
        print("\n(No doc written.)")
        return 0

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


def cmd_help(kb: KB, args) -> int:
    """Print grouped overview with copy-pasteable examples."""
    print(__doc__)
    print()
    print("=" * 60)
    print("EXAMPLES")
    print("=" * 60)
    print("""
  # Reads
  ldoc get porcelain-roadmap
  ldoc get porcelain-roadmap batch-operations --json
  ldoc body label-and-title
  ldoc show porcelain-roadmap
  ldoc show porcelain-roadmap --plain      # bare id/label format
  ldoc resolve "Batch Operations"
  ldoc label porcelain-roadmap batch-operations
  ldoc neighbors porcelain-roadmap --kind depends_on
  ldoc neighbors porcelain-roadmap batch-operations
  echo -e "porcelain-roadmap\\nbatch-operations" | ldoc show -

  # Search / list
  ldoc find porcelain
  ldoc find label title --or              # OR-mode multi-term
  ldoc find --regex 'batch|multi'
  ldoc find --type decision --status living
  ldoc ls --type principle
  ldoc log --since 2026-06-15T00:00:00Z --limit 10
  ldoc count

  # Mutations
  ldoc new --type decision --title "My Decision" --level preference \\
       --depends-on cognitive-load
  ldoc new --type decision --title "Test" --dry-run
  ldoc set porcelain-roadmap --title "New Title"
  ldoc set porcelain-roadmap --body -         # read body from stdin
  echo "new body text" | ldoc edit porcelain-roadmap
  ldoc link porcelain-roadmap --depends-on batch-operations
  ldoc link porcelain-roadmap --depends-on batch-operations --dry-run
  ldoc unlink porcelain-roadmap --depends-on batch-operations
  ldoc history porcelain-roadmap --add "Updated approach"

  # Maintenance
  ldoc validate
  ldoc reindex
  ldoc edges
  ldoc review new --since 2026-06-15T00:00:00Z
  ldoc review list
  ldoc review show <review-id>
  ldoc review sign <review-id> --as "Your Name"
""")
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

VALID_TYPES_SORTED = sorted(VALID_TYPES)
VALID_LEVELS_SORTED = sorted(VALID_LEVELS)
VALID_STATES_SORTED = sorted(VALID_STATES)
VALID_STATUSES_SORTED = sorted(VALID_STATUSES)
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
    p = sub.add_parser("get", help="Show frontmatter summary for one or more docs.")
    p.add_argument("refs", nargs="+", metavar="ref",
                   help="id | label | title; or '-' to read from stdin (one per line).")
    p.add_argument("--json", action="store_true")

    # --- body ---
    p = sub.add_parser("body", help="Print the body text of one or more docs.")
    p.add_argument("refs", nargs="+", metavar="ref",
                   help="id | label | title; or '-' to read from stdin.")

    # --- show ---
    p = sub.add_parser("show", help="Show full doc with resolved edge links.")
    p.add_argument("refs", nargs="+", metavar="ref",
                   help="id | label | title; or '-' to read from stdin.")
    p.add_argument("--json", action="store_true")
    p.add_argument("--plain", action="store_true",
                   help="Use plain id/label format for edge lists (not typed wiki-links).")

    # --- find ---
    p = sub.add_parser("find", help="Search/filter docs. Multiple terms = AND (use --or for OR).")
    p.add_argument("terms", nargs="*", metavar="term",
                   help="Search terms (matches title + label + body, case-insensitive).")
    p.add_argument("--or", dest="or_mode", action="store_true",
                   help="Combine multiple terms with OR instead of AND.")
    p.add_argument("--regex", default="", metavar="PATTERN",
                   help="Regex pattern applied to title + label + body (re.IGNORECASE).")
    p.add_argument("--type", default="", choices=VALID_TYPES_SORTED + [""])
    p.add_argument("--level", default="", choices=VALID_LEVELS_SORTED + [""])
    p.add_argument("--state", default="", choices=VALID_STATES_SORTED + [""])
    p.add_argument("--status", default="", choices=VALID_STATUSES_SORTED + [""])
    p.add_argument("--scope", default="")
    p.add_argument("--domain", default="")
    p.add_argument("--json", action="store_true")
    p.add_argument("--plain", action="store_true",
                   help="Plain id/label output instead of typed wiki-links.")

    # --- ls ---
    p = sub.add_parser("ls", help="List all docs (optionally filter by type).")
    p.add_argument("--type", default="", choices=VALID_TYPES_SORTED + [""])
    p.add_argument("--json", action="store_true")
    p.add_argument("--plain", action="store_true",
                   help="Plain id/label output instead of typed wiki-links.")

    # --- resolve ---
    p = sub.add_parser("resolve", help="Resolve ref(s) to canonical id(s).")
    p.add_argument("refs", nargs="+", metavar="ref",
                   help="id | label | title; or '-' to read from stdin.")

    # --- label ---
    p = sub.add_parser("label", help="Print '<Type>: <Title>' for ref(s).")
    p.add_argument("refs", nargs="+", metavar="ref",
                   help="id | label | title; or '-' to read from stdin.")

    # --- neighbors ---
    p = sub.add_parser("neighbors", help="Show neighbors of one or more docs.")
    p.add_argument("refs", nargs="+", metavar="ref",
                   help="id | label | title; or '-' to read from stdin.")
    p.add_argument("--kind", default="all",
                   choices=["depends_on", "references", "dependents", "referenced_by", "all"])
    p.add_argument("--json", action="store_true")
    p.add_argument("--plain", action="store_true",
                   help="Plain id/label edge format instead of typed wiki-links.")

    # --- graph ---
    p = sub.add_parser("graph", help="BFS traversal over depends_on edges.")
    p.add_argument("ref", help="id | label | title")
    p.add_argument("--depth", type=int, default=1)
    p.add_argument("--direction", default="both", choices=["up", "down", "both"])
    p.add_argument("--json", action="store_true")

    # --- log ---
    p = sub.add_parser("log",
                       help="Recent-changes view (created/edited, newest first). "
                            "Read-only; does NOT create a review record.")
    p.add_argument("--since", default="", metavar="ISO8601",
                   help="Show only changes at or after this ISO 8601 UTC timestamp.")
    p.add_argument("--limit", type=int, default=None, metavar="N",
                   help="Maximum number of events to show.")
    p.add_argument("--json", action="store_true")

    # --- count ---
    p = sub.add_parser("count", help="Doc and edge count statistics.")
    p.add_argument("--json", action="store_true")

    # --- new ---
    p = sub.add_parser("new", help="Create a new doc.",
                       description=(
                           "Type-aware defaults:\n"
                           "  --level:  incidental (override with --level)\n"
                           "  --state:  actual     (override with --state)\n"
                           "  --status: living     (override with --status)\n"
                           "  --label:  auto-derived as Title-Case from title words\n"
                           "            (up to ~24 chars, word boundaries only)\n"
                           "Edge refs validated before writing; unresolved refs cause an error."
                       ),
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--type", required=True, choices=VALID_TYPES_SORTED)
    p.add_argument("--title", required=True)
    p.add_argument("--label", default="",
                   help="Short Title-Case label; auto-derived from title if omitted.")
    p.add_argument("--level", default="incidental", choices=VALID_LEVELS_SORTED)
    p.add_argument("--state", default="actual", choices=VALID_STATES_SORTED)
    p.add_argument("--status", default="living", choices=VALID_STATUSES_SORTED)
    p.add_argument("--depends-on", default="", dest="depends_on",
                   help="Comma-separated ids/labels/titles. Validated before write.")
    p.add_argument("--references", default="",
                   help="Comma-separated ids/labels/titles. Validated before write.")
    p.add_argument("--tags-domain", default="", dest="tags_domain")
    p.add_argument("--tags-scope", default="", dest="tags_scope")
    p.add_argument("--kind", default="", choices=REFERENCE_KIND_CHOICES + [""])
    p.add_argument("--source", default="")
    p.add_argument("--body", default="", help="Body text or '-' to read from stdin.")
    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="Preview what would be created without writing.")

    # --- set ---
    p = sub.add_parser("set", help="Update frontmatter fields or body of a doc.")
    p.add_argument("ref", help="id | label | title")
    p.add_argument("--title", default=None)
    p.add_argument("--label", default=None)
    p.add_argument("--level", default=None, choices=VALID_LEVELS_SORTED)
    p.add_argument("--state", default=None, choices=VALID_STATES_SORTED)
    p.add_argument("--status", default=None, choices=VALID_STATUSES_SORTED)
    p.add_argument("--type", default=None, choices=VALID_TYPES_SORTED)
    p.add_argument("--body", default=None,
                   help="Replace body: TEXT value or '-' to read from stdin.")
    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="Preview what would change without writing.")

    # --- edit ---
    p = sub.add_parser("edit",
                       help="Replace a doc's body from stdin (alias for: set <ref> --body -).")
    p.add_argument("ref", help="id | label | title")

    # --- link ---
    p = sub.add_parser("link", help="Add edge(s) to a doc.")
    p.add_argument("ref", help="id | label | title")
    p.add_argument("--depends-on", default="", dest="depends_on",
                   help="Comma-separated ids/labels/titles. Validated before write.")
    p.add_argument("--references", default="",
                   help="Comma-separated ids/labels/titles. Validated before write.")
    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="Preview the edges that would be added without writing.")

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
    sub.add_parser("validate", help="Run structural integrity checks.")

    # --- reindex ---
    sub.add_parser("reindex", help="Rebuild docs/.index/ artifacts.")

    # --- edges ---
    p = sub.add_parser("edges", help="Print forward/reverse edge maps.")
    p.add_argument("--json", action="store_true")

    # --- review ---
    p_rev = sub.add_parser("review", help="Manage review summaries in the reviews/ ledger.")
    rev_sub = p_rev.add_subparsers(dest="review_verb", metavar="verb")
    rev_sub.required = True

    p_rn = rev_sub.add_parser("new", help="Create a new review summary record.")
    p_rn.add_argument("--since", default="",
                      help="ISO 8601 UTC timestamp; scan docs/ for changes since this time.")
    p_rn.add_argument("--touched", default="",
                      help="Comma-separated doc ids/refs to include explicitly.")
    p_rn.add_argument("--summary", default="",
                      help="Summary body text, or '-' to read from stdin.")

    p_rl = rev_sub.add_parser("list", help="List review records.")
    p_rl.add_argument("--unsigned-by", default="", dest="unsigned_by",
                      help="Show only records NOT signed by this name.")

    p_rs = rev_sub.add_parser("show", help="Show a review record.")
    p_rs.add_argument("ref", help="Review record id (or unique prefix/substring).")

    p_rsg = rev_sub.add_parser("sign", help="Sign a review record.")
    p_rsg.add_argument("ref", help="Review record id (or unique prefix/substring).")
    p_rsg.add_argument("--as", dest="as_who", required=True,
                       help="Your name (free-text signature).")

    # --- help ---
    sub.add_parser("help", help="Show overview with grouped verbs and copy-pasteable examples.")

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
    "log": cmd_log,
    "count": cmd_count,
    "new": cmd_new,
    "set": cmd_set,
    "edit": cmd_edit,
    "link": cmd_link,
    "unlink": cmd_unlink,
    "history": cmd_history,
    "ingest-raw": cmd_ingest_raw,
    "validate": cmd_validate,
    "reindex": cmd_reindex,
    "edges": cmd_edges,
    "review": cmd_review,
    "help": cmd_help,
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
