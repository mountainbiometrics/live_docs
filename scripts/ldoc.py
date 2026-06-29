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
    neighbors <ref> [<ref2> ...]
        [--kind requires|belongs_to|relates|provenance|superseded_by|required_by|children|dependents|provenance_of|all]
        [--json]

  ── Orient / search / list ──
    map [--json]                    # entry points (signpost roots) — start here
    find [term ...] [--or] [--regex PAT]
         [--type] [--level] [--status] [--scope] [--domain] [--json] [--plain]
    ls [--type] [--json] [--plain]
    orphans [--json] [--plain]
    log [--since <ISO>] [--limit N] [--json]
    count [--json]
    domains [--json] [--plain]

  ── Graph ──
    graph <ref> [--depth N] [--direction up|down|both] [--json]
    edges [--json]

  ── Mutations ──
    new --type T --title T [--label L] [--summary S] [--level L] [--status S]
        [--requires a,b] [--belongs-to|--parent a,b] [--relates a,b]
        [--provenance a,b] [--superseded-by a,b]
        [--tags-domain d] [--tags-scope s]
        [--kind K] [--source S] [--origin O] [--medium M] [--authored-at A]
        [--body T|-] [--dry-run]
    set <ref> [--title] [--label] [--summary] [--level] [--status] [--type]
              [--scope] [--domain] [--body -|TEXT] [--dry-run]
    edit <ref>   (alias: set <ref> --body -)
    link <ref> [--requires a,b] [--belongs-to|--parent a,b] [--relates a,b]
               [--provenance a,b] [--superseded-by a,b] [--dry-run]
    unlink <ref> [--requires a,b] [--belongs-to|--parent a,b] [--relates a,b]
                 [--provenance a,b] [--superseded-by a,b]
    history <ref> --add "summary"
    rm <ref> [--force] [--dry-run]
    ingest-raw (--from-file P | --body T|-) --source S [--title T] [--label L]
               [--origin O] [--medium M] [--authored-at A]
               [--parent-raw R] [--inherit-from R] [--shard-depth N]

  ── Inbox pipeline ──
    inbox add (--from-file P | --body T|-) [--title T] [--source S]
              [--origin O] [--medium M] [--authored-at A]
    inbox list
    promote <ref> [--all]
    raw list [--pending]
    raw show <ref>
    raw children <ref>
    raw mark-ingested <ref>

  ── Maintenance ──
    validate
    reindex
    viewer [--out PATH]
    review <new|list|show|sign> ...
    config [--list] [key] [value]   # user prefs in ~/.config/live_docs/config.toml

  ── Help ──
    help
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Ensure scripts/ is on sys.path so livedocs is importable from any CWD.
_scripts_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(_scripts_dir))

from livedocs import KB, VALID_TYPES, VALID_LEVELS, VALID_STATUSES, VALID_REFERENCE_KINDS
from livedocs import ReviewLedger, generate_id, build_raw_frontmatter


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


def _fields_row(kb: KB, doc_id: str, fields: list[str]) -> str:
    """Return a TSV row for doc_id, extracting named fields from the in-memory doc."""
    doc = kb._docs.get(doc_id, {})
    values = []
    for f in fields:
        if f == "id":
            val = doc_id
        elif f in ("title", "display"):
            val = doc.get("title", "") or doc.get("label", "")
        elif f == "history":
            val = str(len(doc.get("history", [])))
        else:
            raw = doc.get(f, "")
            if isinstance(raw, list):
                raw = ",".join(str(v) for v in raw)
            val = str(raw) if raw else ""
        values.append(val)
    return "\t".join(values)


def _split_csv(val: str) -> list[str]:
    return [s.strip() for s in (val or "").split(",") if s.strip()]


def _parse_fields(args) -> list[str] | None:
    parsed = _split_csv(getattr(args, "fields", None) or "")
    return parsed if parsed else None


def _apply_count_limit(results: list, args) -> tuple[list, bool]:
    """Slice results by --limit, then print count and signal early-exit if --count."""
    if args.limit is not None:
        results = results[:args.limit]
    if args.count:
        print(len(results))
        return results, True
    return results, False


def _print_result(kb: "KB", r: dict, fields: list[str] | None, plain: bool, snippet: bool = False) -> None:
    if fields:
        print(_fields_row(kb, r["id"], fields))
    elif plain:
        label_part = f" [{r['label']}]" if r.get("label") else ""
        print(f"{r['id']}{label_part}  {r.get('display', '')}")
    else:
        print(f"[{r.get('display', '')}]({r['id']}.md)")
    if snippet and r.get("snippet") and not fields:
        print(f"  {r['snippet']}")


def _kb(fn, *a, **kw) -> bool:
    """Call fn(*a, **kw); print error and return True on ValueError."""
    try:
        fn(*a, **kw)
        return False
    except ValueError as e:
        _err(str(e))
        return True


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

    fields = _parse_fields(args)

    if fields:
        for ref in refs:
            try:
                result = kb.get(ref)
            except ValueError as e:
                _err(str(e))
                return 1
            print(_fields_row(kb, result["id"], fields))
        return 0

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
        summary = fm.get("summary", "")
        if summary:
            print(f"summary: {summary}")
        print(f"type:   {fm.get('type', '')}")
        print(f"status: {fm.get('status', '')}  level: {fm.get('level', '')}")
        print(f"created: {fm.get('created', '')}")
        print(f"domain: {fm.get('domain', [])}  keywords: {fm.get('keywords', [])}  scope: {fm.get('scope', '') or '(none)'}")
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
        summary = fm.get("summary", "")
        if summary:
            print(f"  summary: {summary}")
        print(f"  type:   {fm.get('type','')}  status: {fm.get('status','')}  "
              f"level: {fm.get('level','')}")
        own_scope = fm.get('scope', '') or '(none)'
        eff_scope = result.get('effective_scope', [])
        print(f"  domain: {fm.get('domain',[])}  scope: {own_scope}")
        print(f"  effective scope: {eff_scope}")
        print(f"  created: {fm.get('created','')}")
        print(f"{'='*60}")
        print()

        print("REQUIRES:")
        print(_fmt_edge_list(result["requires"], plain=plain))
        print()
        print("BELONGS TO:")
        print(_fmt_edge_list(result["belongs_to"], plain=plain))
        print()
        print("RELATES:")
        print(_fmt_edge_list(result["relates"], plain=plain))
        print()
        print("PROVENANCE:")
        print(_fmt_edge_list(result["provenance"], plain=plain))
        print()
        print("SUPERSEDED BY:")
        print(_fmt_edge_list(result["superseded_by"], plain=plain))
        print()
        print("REQUIRED BY:")
        print(_fmt_edge_list(result["required_by"], plain=plain))
        print()
        print("CHILDREN:")
        print(_fmt_edge_list(result["children"], plain=plain))
        print()
        print("PROVENANCE OF:")
        print(_fmt_edge_list(result["provenance_of"], plain=plain))
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
    fields = _parse_fields(args)

    try:
        results = kb.find(
            terms=terms if terms else None,
            or_mode=getattr(args, "or_mode", False),
            regex=getattr(args, "regex", None) or None,
            type=args.type or None,
            level=args.level or None,
            status=args.status or None,
            scope=args.scope or None,
            domain=args.domain or None,
        )
    except ValueError as e:
        _err(str(e))
        return 1

    results, done = _apply_count_limit(results, args)
    if done:
        return 0

    if args.json:
        _json(results)
        return 0

    if not results:
        print("(no results)")
        return 0

    for r in results:
        _print_result(kb, r, fields, plain, snippet=True)

    return 0


def cmd_ls(kb: KB, args) -> int:
    plain = getattr(args, "plain", False)
    fields = _parse_fields(args)
    try:
        results = kb.ls(type=args.type or None)
    except Exception as e:
        _err(str(e))
        return 1

    results, done = _apply_count_limit(results, args)
    if done:
        return 0

    if args.json:
        _json(results)
        return 0

    for r in results:
        _print_result(kb, r, fields, plain)

    return 0


def cmd_orphans(kb: KB, args) -> int:
    """List docs outside the belongs_to hierarchy (no belongs_to in or out)."""
    plain = getattr(args, "plain", False)
    fields = _parse_fields(args)
    try:
        results = kb.orphans()
    except Exception as e:
        _err(str(e))
        return 1

    results, done = _apply_count_limit(results, args)
    if done:
        return 0

    if args.json:
        _json(results)
        return 0

    if not results:
        print("(no orphans)")
        return 0

    for r in results:
        _print_result(kb, r, fields, plain)

    return 0


def cmd_map(kb: KB, args) -> int:
    """Orientation map: the topological entry points (signpost roots) of the store."""
    try:
        overview = kb.map_overview()
    except Exception as e:
        _err(str(e))
        return 1

    if args.json:
        _json(overview)
        return 0

    signposts = overview["signposts"]
    floating = overview["floating"]

    print(f"# Store map — {overview['total']} docs, "
          f"{len(signposts)} entry point(s), {len(floating)} floating\n")

    if signposts:
        print("## Entry points (signpost roots, biggest first)\n")
        for s in signposts:
            scope = f"  scope: {', '.join(s['scope'])}" if s["scope"] else ""
            print(f"[{s['display']}]({s['id']}.md)  "
                  f"({s['descendants']} descendants){scope}")
            if s["summary"]:
                print(f"  {s['summary']}")
            for c in s["children"]:
                tail = f" ({c['descendants']} below)" if c["descendants"] else ""
                print(f"    → [{c['display']}]({c['id']}.md){tail}")
                if c["summary"]:
                    print(f"        {c['summary']}")
            print()

    if floating:
        print("## Floating (roots with no descendants — orphans & standalone)\n")
        for f in floating:
            print(f"[{f['display']}]({f['id']}.md)")
            if f["summary"]:
                print(f"  {f['summary']}")
        print()

    if not signposts and not floating:
        print("(empty store)")

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

    if getattr(args, "count", False):
        for ref in refs:
            try:
                result = kb.neighbors(ref, kind=args.kind)
            except ValueError as e:
                _err(str(e))
                return 1
            total = sum(len(v) for v in result.values())
            if len(refs) > 1:
                print(f"{ref}\t{total}")
            else:
                print(total)
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
    print("By status:")
    for k, v in stats["by_status"].items():
        print(f"  {k:20s}  {v}")
    print()
    print(f"requires edges:      {stats['requires_count']}")
    print(f"belongs_to edges:    {stats['belongs_to_count']}")
    print(f"relates edges:       {stats['relates_count']}")
    print(f"provenance edges:    {stats['provenance_count']}")
    print(f"superseded_by edges: {stats['superseded_by_count']}")

    return 0


def cmd_domains(kb: KB, args) -> int:
    """Domain registry: list every distinct domain tag in use, with doc counts."""
    try:
        rows = kb.domain_counts()
    except Exception as e:
        _err(str(e))
        return 1

    plain = getattr(args, "plain", False)

    if args.json:
        _json(rows)
        return 0

    if not rows:
        if plain:
            pass  # plain empty-state: print nothing, exit 0
        else:
            print("domains — none in use")
        return 0

    if plain:
        for r in rows:
            print(f"{r['count']}\t{r['domain']}")
        return 0

    # Human output
    total_distinct = len(rows)
    total_docs = sum(r["count"] for r in rows)
    print(f"domains — {total_distinct} distinct, {total_docs} docs tagged")
    # Width of the widest domain name for alignment
    max_name_len = max(len(r["domain"]) for r in rows)
    for r in rows:
        print(f"  {r['domain']:<{max_name_len}}  {r['count']}")

    return 0


def cmd_new(kb: KB, args) -> int:
    edges = _parse_edge_args(args)
    domain_tags = [s.strip() for s in args.tags_domain.split(",") if s.strip()] \
        if args.tags_domain else []
    keyword_tags = [s.strip() for s in args.tags_keywords.split(",") if s.strip()] \
        if getattr(args, "tags_keywords", "") else []
    scope_tags = [s.strip() for s in args.tags_scope.split(",") if s.strip()] \
        if args.tags_scope else []

    # Edge-ref validation: validate before writing
    if any(edges.values()):
        unresolved = kb.validate_edge_refs(**edges)
        if unresolved:
            _err(
                f"Unresolved edge ref(s): {', '.join(repr(r) for r in unresolved)}. "
                f"Check with: ldoc resolve <ref>"
            )
            return 1

    # Body
    if args.body == "-":
        body = sys.stdin.read()
    elif args.body:
        body = args.body
    else:
        body = ""

    # --dry-run preview
    if getattr(args, "dry_run", False):
        # label is required; title is optional and falls back to the label.
        label = args.label
        title = args.title or label
        print("## DRY RUN — would create:\n")
        print(f"  type:    {args.type}")
        print(f"  label:   {label}")
        print(f"  title:   {title}")
        if args.summary:
            print(f"  summary: {args.summary}")
        print(f"  level:   {args.level}")
        print(f"  status:  {args.status}")
        for field, refs in edges.items():
            if refs:
                print(f"  {field}: {refs}")
        if body.strip():
            print(f"\n  body preview:\n    {body.strip()[:200]}")
        print("\n(No doc written.)")
        return 0

    try:
        doc_id = kb.new(
            type=args.type,
            label=args.label,
            title=args.title or "",
            summary=args.summary or "",
            level=args.level,
            status=args.status,
            **edges,
            tags_domain=domain_tags,
            tags_keywords=keyword_tags,
            tags_scope=scope_tags,
            body=body,
            kind=args.kind or "",
            source=args.source or "",
            origin=getattr(args, "origin", "") or "",
            medium=getattr(args, "medium", "") or "",
            authored_at=getattr(args, "authored_at", "") or "",
        )
    except Exception as e:
        _err(str(e))
        return 1

    print(f"id:   {doc_id}")
    print(f"path: {kb.docs_dir / doc_id}.md")
    return 0


def cmd_set(kb: KB, args) -> int:
    # Conflict: stdin can't serve both refs and body
    body_arg = getattr(args, "body", None)
    if args.refs == ["-"] and body_arg == "-":
        _err("Cannot use '-' for both refs and --body. Provide refs explicitly when using --body -.")
        return 1

    set_fields = {}
    if args.title is not None:
        set_fields["title"] = args.title
    if args.summary is not None:
        set_fields["summary"] = args.summary
    if args.label is not None:
        set_fields["label"] = args.label.strip()
    if args.level is not None:
        set_fields["level"] = args.level
    if args.status is not None:
        set_fields["status"] = args.status
    if args.type is not None:
        set_fields["type"] = args.type
    if args.scope is not None:
        set_fields["scope"] = args.scope
    if args.domain is not None:
        set_fields["domain"] = _split_csv(args.domain)
    if getattr(args, "keywords", None) is not None:
        set_fields["keywords"] = _split_csv(args.keywords)

    # --body: read new body from stdin or inline (before resolving refs, which may also use stdin)
    new_body = None
    if body_arg == "-":
        new_body = sys.stdin.read()
    elif body_arg:
        new_body = body_arg

    refs = _resolve_refs(kb, args.refs)
    if refs is None:
        return 1

    if not set_fields and new_body is None:
        _err("No fields specified. Use --title, --label, --summary, --level, --status, --type, --scope, --domain, --keywords, or --body.")
        return 1

    note = getattr(args, "note", "")

    # --dry-run preview
    if getattr(args, "dry_run", False):
        print("## DRY RUN — would update:\n")
        for ref in refs:
            try:
                doc_id = kb.resolve(ref)
            except ValueError as e:
                _err(str(e))
                return 1
            print(f"  doc: {doc_id}")
            for k, v in set_fields.items():
                print(f"  {k}: {v!r}")
            if new_body is not None:
                print(f"  body: (replace, {len(new_body)} chars)")
            if note:
                print(f"  --note: {note!r}")
        print("\n(No doc written.)")
        return 0

    for ref in refs:
        if set_fields and _kb(kb.set, ref, **set_fields):
            return 1
        if new_body is not None and _kb(kb.set_body, ref, new_body):
            return 1
        if note and _kb(kb.add_history, ref, note):
            return 1

    print(f"Updated {', '.join(refs)}")
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


def _parse_edge_args(args) -> dict:
    """Parse all edge CLI args into lists of ref strings."""
    return {
        "requires": _split_csv(getattr(args, "requires", "") or ""),
        "belongs_to": _split_csv(getattr(args, "belongs_to", "") or ""),
        "relates": _split_csv(getattr(args, "relates", "") or ""),
        "provenance": _split_csv(getattr(args, "provenance", "") or ""),
        "superseded_by": _split_csv(getattr(args, "superseded_by", "") or ""),
    }


def cmd_link(kb: KB, args) -> int:
    refs = _resolve_refs(kb, args.refs)
    if refs is None:
        return 1

    edges = _parse_edge_args(args)

    if not any(edges.values()):
        _err("Specify at least one of: --requires, --belongs-to (--parent), --relates, "
             "--provenance, --superseded-by.")
        return 1

    # Edge-ref validation
    unresolved = kb.validate_edge_refs(**edges)
    if unresolved:
        _err(
            f"Unresolved edge ref(s): {', '.join(repr(r) for r in unresolved)}. "
            f"Check with: ldoc resolve <ref>"
        )
        return 1

    replace = getattr(args, "replace", False)
    note = getattr(args, "note", "")

    # --dry-run preview
    if getattr(args, "dry_run", False):
        print("## DRY RUN — would link:\n")
        print(f"  refs: {refs}")
        for field, edge_refs in edges.items():
            if edge_refs:
                print(f"  --{field.replace('_', '-')}: {edge_refs}")
        if replace and edges.get("belongs_to"):
            print("  (existing belongs_to edges will be replaced)")
        if note:
            print(f"  --note: {note!r}")
        print("\n(No doc written.)")
        return 0

    for ref in refs:
        if _kb(kb.link, ref, **{k: v or None for k, v in edges.items()},
               replace_belongs_to=replace):
            return 1
        if note and _kb(kb.add_history, ref, note):
            return 1

    print(f"Linked {', '.join(refs)}")
    return 0


def cmd_unlink(kb: KB, args) -> int:
    refs = _resolve_refs(kb, args.refs)
    if refs is None:
        return 1

    edges = _parse_edge_args(args)

    if not any(edges.values()):
        _err("Specify at least one of: --requires, --belongs-to (--parent), --relates, "
             "--provenance, --superseded-by.")
        return 1

    note = getattr(args, "note", "")

    for ref in refs:
        if _kb(kb.unlink, ref, **{k: v or None for k, v in edges.items()}):
            return 1
        if note and _kb(kb.add_history, ref, note):
            return 1

    print(f"Unlinked {', '.join(refs)}")
    return 0


def cmd_history(kb: KB, args) -> int:
    if not args.add:
        _err("Specify --add 'summary text'.")
        return 1

    refs = _resolve_refs(kb, args.refs)
    if refs is None:
        return 1

    for ref in refs:
        if _kb(kb.add_history, ref, args.add):
            return 1

    print(f"History entry added to {', '.join(refs)}")
    return 0


def _normalize_raw_pointer(ref: str):
    """Resolve a raw ref (id, substring, or 'raw/<id>.md') to ('raw/<id>.md', id).

    Returns (None, None) if it does not resolve to a raw file.
    """
    from livedocs import RAW_DIR
    if not ref:
        return None, None
    m = re.search(r"\d{14}", ref)
    cand = m.group(0) if m else ref
    path = _inbox_resolver(cand, RAW_DIR)
    if path is None:
        return None, None
    return f"raw/{path.stem}.md", path.stem


def cmd_rm(kb: KB, args) -> int:
    """Delete a doc from the store; block when any inbound edge exists unless --force."""
    import subprocess

    from livedocs.graph import inbound_edges

    try:
        doc_id = kb.resolve(args.ref)
    except ValueError as e:
        _err(str(e))
        return 1

    inbound = inbound_edges(kb._docs, doc_id)

    doc = kb.get(doc_id)
    label = doc.get("label", doc_id)
    title = doc.get("title", label)

    if args.dry_run:
        print("## DRY RUN — would delete:\n")
        print(f"  id:    {doc_id}")
        print(f"  label: {label}")
        print(f"  title: {title}")
        if inbound:
            print(f"\n  Inbound edges ({len(inbound)}):")
            for referrer_id, field in inbound:
                ref_doc = kb._docs.get(referrer_id, {})
                ref_label = ref_doc.get("label", referrer_id)
                print(f"    {referrer_id} [{ref_label}]  ←  {field}")
            if args.force:
                print("\n  --force: would strip all inbound edges, then delete.")
            else:
                print("\n  BLOCKED: inbound edges present (use --force to strip and delete).")
        else:
            print("\n  No inbound edges — would delete cleanly.")
        print("\n(No doc deleted.)")
        return 0

    if inbound and not args.force:
        lines = "\n".join(
            f"  {referrer_id}  {field}  ({kb._docs.get(referrer_id, {}).get('label', '')})"
            for referrer_id, field in inbound
        )
        _err(
            f"Cannot delete {doc_id}: {len(inbound)} inbound edge(s):\n{lines}\n\n"
            "Use --force to strip all inbound edges and delete."
        )
        return 1

    if args.force and inbound:
        stripped = kb.strip_inbound_edges(doc_id, inbound=inbound)
        print(f"Stripped {len(stripped)} inbound edge(s) from {len({r for r, _ in stripped})} doc(s):")
        for referrer_id, field in stripped:
            ref_label = kb._docs.get(referrer_id, {}).get("label", referrer_id)
            print(f"  {referrer_id} [{ref_label}]  {field}")

    (kb.docs_dir / f"{doc_id}.md").unlink()
    print(f"Deleted {doc_id}  ({label})")

    script = Path(__file__).resolve().parent / "reindex.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=False)
    return result.returncode


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

    from livedocs import RAW_DIR

    origin = getattr(args, "origin", "") or ""
    medium = getattr(args, "medium", "") or ""
    authored_at = getattr(args, "authored_at", "") or ""
    source = args.source or ""
    captured = ""
    parent_raw = ""
    shard_depth = getattr(args, "shard_depth", None)

    # --inherit-from: copy provenance from a parent raw; implies --parent-raw and,
    # unless overridden, sets shard_depth = parent.shard_depth + 1.
    inherit = getattr(args, "inherit_from", "") or ""
    if inherit:
        ptr, pid = _normalize_raw_pointer(inherit)
        if ptr is None:
            _err(f"--inherit-from: raw item {inherit!r} not found.")
            return 1
        ppath = RAW_DIR / f"{pid}.md"
        origin = origin or _read_frontmatter_field(ppath, "origin")
        medium = medium or _read_frontmatter_field(ppath, "medium")
        authored_at = authored_at or _read_frontmatter_field(ppath, "authored_at")
        captured = _read_frontmatter_field(ppath, "captured")
        source = source or _read_frontmatter_field(ppath, "original_source")
        parent_raw = ptr
        if shard_depth is None:
            pd = _read_frontmatter_field(ppath, "shard_depth")
            try:
                shard_depth = (int(pd) if pd else 0) + 1
            except ValueError:
                shard_depth = 1

    # Explicit --parent-raw overrides / sets the parent pointer.
    pr = getattr(args, "parent_raw", "") or ""
    if pr:
        ptr, _pid = _normalize_raw_pointer(pr)
        if ptr is None:
            _err(f"--parent-raw: raw item {pr!r} not found.")
            return 1
        parent_raw = ptr

    if not source:
        _err("--source is required (or use --inherit-from to copy it from a parent raw).")
        return 1

    try:
        raw_id = kb.ingest_raw(
            source=source,
            body=body,
            from_file=from_file,
            title=args.title or "",
            label=args.label or "",
            origin=origin,
            medium=medium,
            authored_at=authored_at,
            captured=captured,
            parent_raw=parent_raw,
            shard_depth=shard_depth or 0,
        )
    except Exception as e:
        _err(str(e))
        return 1

    print(f"id:   {raw_id}")
    print(f"path: {RAW_DIR / raw_id}.md")
    return 0


def _yaml_str_inbox(value: str) -> str:
    """Wrap value in double-quotes, escaping any inner double-quotes."""
    return '"' + value.replace('"', '\\"') + '"'


def _inbox_resolver(ref: str, search_dir: Path) -> Path | None:
    """
    Resolve a ref against a flat directory of <id>.md files.

    Matches (in order):
    1. Exact id: <ref>.md exists
    2. Unique filename substring: exactly one file whose stem contains <ref>
    3. Unique title substring (case-insensitive) in frontmatter

    Returns the Path on a unique match, None if not found or ambiguous.
    Prints an error to stderr on ambiguity.
    """
    candidates = list(search_dir.glob("*.md"))

    # 1. Exact id match
    exact = search_dir / f"{ref}.md"
    if exact.exists():
        return exact

    # 2. Filename stem substring
    stem_matches = [p for p in candidates if ref in p.stem]
    if len(stem_matches) == 1:
        return stem_matches[0]
    if len(stem_matches) > 1:
        _err(f"Ref {ref!r} is ambiguous (matches: {', '.join(p.stem for p in stem_matches)}). "
             f"Use a more specific ref or the exact id.")
        return None

    # 3. Title substring in frontmatter (case-insensitive)
    pattern = re.compile(re.escape(ref), re.IGNORECASE)
    title_matches = []
    for p in candidates:
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        # Extract title from frontmatter: look for `title: "..." or title: ...`
        for line in text.split("\n"):
            if line.startswith("title:"):
                title_val = line[len("title:"):].strip().strip('"').strip("'")
                if pattern.search(title_val):
                    title_matches.append(p)
                break
    if len(title_matches) == 1:
        return title_matches[0]
    if len(title_matches) > 1:
        _err(f"Ref {ref!r} is ambiguous by title (matches: "
             f"{', '.join(p.stem for p in title_matches)}). "
             f"Use a more specific ref or the exact id.")
        return None

    return None


def _read_frontmatter_field(path: Path, field: str) -> str:
    """Return the value of a frontmatter scalar field, or '' if absent."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    in_fm = False
    for line in text.split("\n"):
        if line == "---":
            if not in_fm:
                in_fm = True
                continue
            else:
                break
        if in_fm and line.startswith(f"{field}:"):
            val = line[len(f"{field}:"):].strip().strip('"').strip("'")
            return val
    return ""


def _referenced_raw_ids(kb: KB) -> set:
    """Return the set of raw ids referenced by any graph doc.

    A raw clipping counts as ingested-by-graph-evidence when some doc points at
    it via its `source` path (e.g. "raw/<id>.md") or lists it in `provenance`.
    This is the read-only half of the hybrid ingest-state check.
    """
    refs = set()
    for d in kb._docs.values():
        src = d.get("source") or ""
        for m in re.findall(r"\d{14}", str(src)):
            refs.add(m)
        for pid in (d.get("provenance") or []):
            refs.add(str(pid))
    return refs


def _read_frontmatter_fields(path: Path, *fields: str) -> dict:
    """Read multiple frontmatter scalar fields in a single file pass."""
    result = {f: "" for f in fields}
    remaining = set(fields)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return result
    in_fm = False
    for line in text.split("\n"):
        if line == "---":
            if not in_fm:
                in_fm = True
                continue
            break
        if not in_fm or not remaining:
            continue
        for field in list(remaining):
            if line.startswith(f"{field}:"):
                result[field] = line[len(f"{field}:"):].strip().strip('"').strip("'")
                remaining.discard(field)
                break
    return result


def _raw_inventory(kb: KB) -> dict:
    """Build {raw_id: record} for every raw clipping, with the signals needed to
    derive ingest-state: the `ingested_at` flag, whether the graph references it,
    its `parent_raw` pointer, and the list of child shards pointing back at it.
    """
    from livedocs import RAW_DIR
    inv: dict = {}
    if not RAW_DIR.exists():
        return inv
    referenced = _referenced_raw_ids(kb)
    for p in sorted(RAW_DIR.glob("*.md")):
        rid = p.stem
        fm = _read_frontmatter_fields(p, "title", "ingested_at", "parent_raw")
        pm = re.search(r"\d{14}", fm["parent_raw"])
        inv[rid] = {
            "id": rid,
            "title": fm["title"],
            "flagged": bool(fm["ingested_at"]),
            "referenced": rid in referenced,
            "parent_id": pm.group(0) if pm else "",
            "children": [],
        }
    for rid, rec in inv.items():
        pid = rec["parent_id"]
        if pid and pid in inv:
            inv[pid]["children"].append(rid)
    return inv


def _raw_done(inv: dict, rid: str, seen: set = None) -> bool:
    """True if a raw is fully processed: a sharded parent whose children are all
    done, or a leaf that has been ingested (flagged or graph-referenced)."""
    seen = seen or set()
    if rid in seen:
        return True  # cycle guard
    seen.add(rid)
    rec = inv.get(rid)
    if not rec:
        return False
    if rec["children"]:
        return all(_raw_done(inv, c, seen) for c in rec["children"])
    return rec["flagged"] or rec["referenced"]


def _raw_status_for(inv: dict, rid: str) -> tuple:
    """Return (status, drift_warning) for a raw item.

    A parent (has child shards) is `sharded` when every child is done, else
    `sharding`; it is never a direct gate-2 unit so never `pending`. A leaf uses
    the hybrid flag+graph cross-check; disagreement surfaces as drift.
    """
    rec = inv[rid]
    if rec["children"]:
        if all(_raw_done(inv, c) for c in rec["children"]):
            return ("sharded", "")
        return ("sharding", "")
    flagged, referenced = rec["flagged"], rec["referenced"]
    if flagged and referenced:
        return ("ingested", "")
    if flagged and not referenced:
        return ("ingested", "DRIFT: flagged ingested but no doc references it")
    if referenced and not flagged:
        return ("ingested", "DRIFT: referenced by docs but not flagged ingested")
    return ("pending", "")


def _print_raw_line(rec: dict, status: str, drift: str) -> None:
    parts = [rec["id"], f"[{status}]"]
    if rec["title"]:
        parts.append(f'"{rec["title"]}"')
    if rec["children"]:
        parts.append(f"({len(rec['children'])} shards)")
    line = "  ".join(parts)
    if drift:
        line += f"   ⚠ {drift}"
    print(line)


def cmd_raw(kb: KB, args) -> int:
    """Dispatch ldoc raw <subverb> commands."""
    verb = args.raw_verb
    if verb == "list":
        return _raw_list(kb, args)
    if verb == "show":
        return _raw_show(kb, args)
    if verb == "children":
        return _raw_children(kb, args)
    if verb == "mark-ingested":
        return _raw_mark_ingested(kb, args)
    _err(f"Unknown raw subcommand: {verb!r}")
    return 1


def _raw_show(kb: KB, args) -> int:
    """Print a raw clipping's full content (frontmatter + verbatim body).

    The raw tier is outside the graph, so `ldoc show`/`body` (graph readers) do
    not resolve raw ids — this is the porcelain read path for a raw file.
    """
    from livedocs import RAW_DIR
    path = _inbox_resolver(args.ref, RAW_DIR)
    if path is None:
        _err(f"Raw item {args.ref!r} not found. Use 'ldoc raw list' to see raw items.")
        return 1
    sys.stdout.write(path.read_text(encoding="utf-8"))
    return 0


def _raw_list(kb: KB, args) -> int:
    """List raw items with derived ingest-state (hybrid flag+graph, shard-aware)."""
    inv = _raw_inventory(kb)
    if not inv:
        print("(no raw items)")
        return 0
    pending_only = getattr(args, "pending", False)
    any_shown = False
    for rid in sorted(inv):
        status, drift = _raw_status_for(inv, rid)
        if pending_only and status != "pending":
            continue
        _print_raw_line(inv[rid], status, drift)
        any_shown = True
    if not any_shown:
        print("(no pending raw items)" if pending_only else "(no raw items)")
    return 0


def _raw_children(kb: KB, args) -> int:
    """List the child shards of a parent raw, each with its ingest-state."""
    from livedocs import RAW_DIR
    path = _inbox_resolver(args.ref, RAW_DIR)
    if path is None:
        _err(f"Raw item {args.ref!r} not found. Use 'ldoc raw list' to see raw items.")
        return 1
    inv = _raw_inventory(kb)
    kids = inv.get(path.stem, {}).get("children", [])
    if not kids:
        print(f"(raw {path.stem} has no child shards)")
        return 0
    for cid in sorted(kids):
        status, drift = _raw_status_for(inv, cid)
        _print_raw_line(inv[cid], status, drift)
    return 0


def _raw_mark_ingested(kb: KB, args) -> int:
    """Write the `ingested_at` flag onto a raw clipping (explicit half of hybrid).

    ingest-reference calls this once decomposition completes. The raw BODY stays
    immutable — only this lifecycle field is added to the frontmatter.
    """
    from datetime import datetime, timezone as _tz
    from livedocs import RAW_DIR
    path = _inbox_resolver(args.ref, RAW_DIR)
    if path is None:
        _err(f"Raw item {args.ref!r} not found. Use 'ldoc raw list' to see raw items.")
        return 1

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        _err(f"Cannot read {path}: {e}")
        return 1

    ts = datetime.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Raw-text surgery: scan for `---` fences by line position and splice in
    # the field.  Fragile: a `---` inside a YAML block scalar or anywhere in
    # the body would fool the fence detector.  The right fix is a shared
    # raw-tier parse/emit layer (analogous to parse_doc/dump_doc for graph
    # docs) so this becomes: parse → set field → dump.  That layer doesn't
    # exist yet; add it here and in _read_frontmatter_field/_read_frontmatter_fields
    # when it does.
    lines = text.split("\n")
    fence = [i for i, l in enumerate(lines) if l == "---"]
    if len(fence) < 2:
        _err(f"{path} has no frontmatter block; cannot mark ingested.")
        return 1
    fm_start, fm_end = fence[0], fence[1]

    for i in range(fm_start + 1, fm_end):
        if lines[i].startswith("ingested_at:"):
            lines[i] = f'ingested_at: "{ts}"'
            break
    else:
        lines.insert(fm_end, f'ingested_at: "{ts}"')

    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Marked ingested: {path.stem}  ingested_at={ts}")
    return 0


def cmd_inbox(kb: KB, args) -> int:
    """Dispatch ldoc inbox <subverb> commands."""
    verb = args.inbox_verb

    if verb == "add":
        return _inbox_add(args)
    elif verb == "list":
        return _inbox_list(args)
    else:
        _err(f"Unknown inbox subcommand: {verb!r}")
        return 1


def _inbox_add(args) -> int:
    """Write one item verbatim into INBOX_DIR with minimal frontmatter."""
    from datetime import datetime, timezone as _tz
    from livedocs import INBOX_DIR

    # Resolve body
    if getattr(args, "from_file", None):
        p = Path(args.from_file)
        if not p.exists():
            _err(f"--from-file path does not exist: {p}")
            return 1
        body = p.read_text(encoding="utf-8")
    elif args.body == "-":
        body = sys.stdin.read()
    elif args.body:
        body = args.body
    else:
        _err("Provide --from-file or --body.")
        return 1

    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    inbox_id = generate_id(INBOX_DIR)
    captured = datetime.now(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    title = getattr(args, "title", "") or ""
    source = getattr(args, "source", "") or ""
    origin = getattr(args, "origin", "") or ""
    medium = getattr(args, "medium", "") or ""
    authored_at = getattr(args, "authored_at", "") or ""

    lines = ["---", f"id: {_yaml_str_inbox(inbox_id)}"]
    if title:
        lines.append(f"title: {_yaml_str_inbox(title)}")
    lines.append("status: inbox")
    if origin:
        lines.append(f"origin: {_yaml_str_inbox(origin)}")
    if medium:
        lines.append(f"medium: {_yaml_str_inbox(medium)}")
    if source:
        lines.append(f"source: {_yaml_str_inbox(source)}")
    if authored_at:
        lines.append(f"authored_at: {_yaml_str_inbox(authored_at)}")
    lines.append(f"captured: {_yaml_str_inbox(captured)}")
    lines.append("---")
    frontmatter = "\n".join(lines)

    content = frontmatter + "\n\n" + body
    if not content.endswith("\n"):
        content += "\n"

    out_path = INBOX_DIR / f"{inbox_id}.md"
    out_path.write_text(content, encoding="utf-8")

    print(f"id:   {inbox_id}")
    print(f"path: {out_path}")
    return 0


def _inbox_list(args) -> int:
    """List items currently in the inbox."""
    from livedocs import INBOX_DIR
    if not INBOX_DIR.exists():
        print("(inbox is empty)")
        return 0

    items = sorted(INBOX_DIR.glob("*.md"))
    # exclude .gitkeep
    items = [p for p in items if p.suffix == ".md"]

    if not items:
        print("(inbox is empty)")
        return 0

    for p in items:
        doc_id = p.stem
        _fm = _read_frontmatter_fields(p, "title", "source", "captured")
        title = _fm["title"]
        source = _fm["source"]
        captured = _fm["captured"]
        label_parts = [doc_id]
        if title:
            label_parts.append(f'"{title}"')
        elif source:
            label_parts.append(f"source: {source}")
        if captured:
            label_parts.append(f"captured: {captured}")
        print("  ".join(label_parts))

    return 0


def cmd_promote(kb: KB, args) -> int:
    """Gate 1: move item(s) from inbox → raw, or explain gate 2 for raw items."""
    from datetime import date as _date
    from livedocs import INBOX_DIR, RAW_DIR

    if getattr(args, "all", False):
        # Drain every inbox item
        if not INBOX_DIR.exists():
            print("Inbox is empty.")
            return 0
        items = sorted(INBOX_DIR.glob("*.md"))
        if not items:
            print("Inbox is empty.")
            return 0
        rc = 0
        for p in items:
            rc = max(rc, _promote_one(p.stem, p, args))
        return rc

    if not args.ref:
        _err("Provide <ref> or --all.")
        return 1

    # Try inbox first
    inbox_path = _inbox_resolver(args.ref, INBOX_DIR)
    if inbox_path is not None:
        return _promote_one(inbox_path.stem, inbox_path, args)

    # Try raw dir — explain gate 2
    raw_path = _inbox_resolver(args.ref, RAW_DIR)
    if raw_path is not None:
        print(
            f"'{args.ref}' is already in raw/ (gate 1 already done).\n"
            f"raw→docs promotion is decomposition — run the ingest-reference skill on that raw id:\n"
            f"  /ingest-reference  (then supply id: {raw_path.stem})"
        )
        return 0

    _err(f"Ref {args.ref!r} not found in inbox or raw. Use 'ldoc inbox list' to see inbox items.")
    return 1


def _promote_one(inbox_id: str, inbox_path: Path, args) -> int:
    """Move one inbox item to raw/, rewriting frontmatter to raw-clipping shape."""
    from datetime import datetime, timezone as _tz
    from livedocs import RAW_DIR

    try:
        body_text = inbox_path.read_text(encoding="utf-8")
    except OSError as e:
        _err(f"Cannot read {inbox_path}: {e}")
        return 1

    # Parse the body out (everything after the closing ---)
    lines = body_text.split("\n")
    in_fm = False
    fm_end = 0
    dash_count = 0
    for i, line in enumerate(lines):
        if line == "---":
            dash_count += 1
            if dash_count == 2:
                fm_end = i
                break

    body_lines = lines[fm_end + 1:] if fm_end else lines
    body = "\n".join(body_lines)
    if body and not body.endswith("\n"):
        body += "\n"

    # Pull useful fields from inbox frontmatter and carry the whole provenance
    # bundle forward — capture-time metadata must not be lost at promotion.
    _ifm = _read_frontmatter_fields(inbox_path, "source", "title", "origin", "medium", "authored_at", "captured")
    original_source = _ifm["source"] or "(promoted from inbox)"
    title = _ifm["title"] or ""
    origin = _ifm["origin"] or ""
    medium = _ifm["medium"] or ""
    authored_at = _ifm["authored_at"] or ""
    captured = _ifm["captured"] or ""

    # Generate a collision-safe id for the raw tier
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_id = generate_id(RAW_DIR)

    imported = datetime.now(_tz.utc).strftime("%Y-%m-%d")

    frontmatter = build_raw_frontmatter(
        raw_id=raw_id,
        source=original_source,
        title=title,
        imported=imported,
        origin=origin,
        medium=medium,
        authored_at=authored_at,
        captured=captured,
    )
    content = frontmatter + "\n\n" + body

    # Write to raw
    raw_path = RAW_DIR / f"{raw_id}.md"
    raw_path.write_text(content, encoding="utf-8")

    # Remove from inbox
    inbox_path.unlink()

    print(f"Promoted: {inbox_id} → {raw_id}")
    print(f"  raw path: {raw_path}")
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


def cmd_viewer(kb: KB, args) -> int:
    """Build the self-contained read-only HTML viewer."""
    from livedocs.viewer import build_viewer

    out_path = Path(args.out).resolve() if args.out else None
    try:
        path, n_docs, n_reviews = build_viewer(out_path=out_path)
    except FileNotFoundError as e:
        _err(str(e))
        return 1
    except OSError as e:
        _err(str(e))
        return 1

    print(f"Wrote {path}")
    print(f"  docs:    {n_docs}")
    print(f"  reviews: {n_reviews}")
    return 0


def cmd_review(kb: KB, args) -> int:
    """Dispatch ldoc review <subverb> commands over the reviews/ ledger."""
    from livedocs import REVIEWS_DIR
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

    # Non-gating guardrail: an explicit body with no --since/--touched produces a
    # record whose `touched` is empty — the body wasn't auto-built from changed
    # docs, so the ledger can't tie it to the graph. Warn, don't fail.
    if body and not since and not touched_refs:
        print(
            "WARNING: review created with an empty `touched` list — the body was "
            "taken as-is, not auto-built from changed docs. Consider --since <ISO8601> "
            "or --touched <refs> so the record links to the docs it covers.",
            file=sys.stderr,
        )

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

    body = ledger.render_body(rec.get("body", "")).strip()
    if body:
        print("SUMMARY:")
        print(body)

    return 0


def _review_sign(ledger: ReviewLedger, args) -> int:
    from livedocs.user_config import get_signer

    as_who = (args.as_who or get_signer() or "").strip()
    if not as_who:
        _err(
            "--as <who> is required when user identity is not configured. "
            'Set with: ldoc config user.name "Your Name" && ldoc config user.email "you@example.com"'
        )
        return 1

    try:
        at = ledger.sign(args.ref, as_who)
    except ValueError as e:
        _err(str(e))
        return 1

    print(f"Signed {args.ref!r} as {as_who!r} at {at}")
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


def cmd_config(_kb, args) -> int:
    from livedocs.user_config import run_config_cli
    return run_config_cli(sys.argv[2:])


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
  ldoc neighbors porcelain-roadmap --kind requires
  ldoc neighbors porcelain-roadmap --kind required_by
  ldoc neighbors porcelain-roadmap --kind children
  ldoc neighbors porcelain-roadmap batch-operations
  echo -e "porcelain-roadmap\\nbatch-operations" | ldoc show -

  # Search / list
  ldoc map                                # orient: entry points + summaries
  ldoc find porcelain
  ldoc find label title --or              # OR-mode multi-term
  ldoc find --regex 'batch|multi'
  ldoc find --type decision --status living
  ldoc ls --type principle
  ldoc orphans                            # docs outside the belongs_to hierarchy
  ldoc log --since 2026-06-15T00:00:00Z --limit 10
  ldoc count
  ldoc domains                            # domain tag registry with counts
  ldoc domains --json
  ldoc domains --plain

  # Mutations
  ldoc new --type decision --label "My Decision" --level preference \\
       --requires cognitive-load
  ldoc new --type decision --label "Test Decision" --dry-run
  ldoc set porcelain-roadmap --title "New Title"
  ldoc set porcelain-roadmap --summary "One-line gist."
  ldoc set porcelain-roadmap --domain "Ingest,Schema Evolution"   # set/clear domain tags
  ldoc set porcelain-roadmap --body -         # read body from stdin
  echo "new body text" | ldoc edit porcelain-roadmap
  ldoc link porcelain-roadmap --requires batch-operations
  ldoc link porcelain-roadmap --relates batch-operations --dry-run
  ldoc unlink porcelain-roadmap --requires batch-operations
  ldoc history porcelain-roadmap --add "Updated approach"
  ldoc rm <ref>                           # delete doc + reindex (blocked if has dependents)
  ldoc rm <ref> --force                   # delete even if dependents exist
  ldoc rm <ref> --dry-run                 # preview without deleting

  # Inbox pipeline (gate 0 → gate 1 → gate 2)
  echo "quick thought" | ldoc inbox add --body - --title "quick thought"
  ldoc inbox add --from-file notes.txt --title "Meeting notes" --source "meeting 2026-06-18"
  ldoc inbox list
  ldoc promote <inbox-id>                # gate 1: inbox → raw
  ldoc promote --all                     # drain entire inbox
  # gate 2: raw → docs via ingest-reference skill
  # (for an item already in raw, promote will print this guidance)

  # Maintenance
  ldoc validate
  ldoc reindex
  ldoc viewer
  ldoc viewer --out build/viewer.html
  ldoc edges
  ldoc review new --since 2026-06-15T00:00:00Z
  ldoc review list
  ldoc review show <review-id>
  ldoc review sign <review-id>              # uses config user.name + user.email
  ldoc review sign <review-id> --as "Your Name <you@example.com>"

  # User identity (~/.config/live_docs/config.toml — git-style)
  ldoc config user.name "Your Name"
  ldoc config user.email "you@example.com"
  ldoc config signer                        # "Name <email>" composite
  ldoc config --list
  ldoc config --bootstrap-from-git
""")
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

VALID_TYPES_SORTED = sorted(VALID_TYPES)
VALID_LEVELS_SORTED = sorted(VALID_LEVELS)
VALID_STATUSES_SORTED = sorted(VALID_STATUSES)
REFERENCE_KIND_CHOICES = sorted(VALID_REFERENCE_KINDS) + [""]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ldoc",
        description="live_docs porcelain CLI — query and mutate the KB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--no-viewer",
        dest="no_viewer",
        action="store_true",
        help="Skip auto-rebuilding build/viewer.html after mutating commands.",
    )
    sub = parser.add_subparsers(dest="subcommand", metavar="subcommand")
    sub.required = True

    # --- get ---
    p = sub.add_parser("get", help="Show frontmatter summary for one or more docs.")
    p.add_argument("refs", nargs="+", metavar="ref",
                   help="id | label | title; or '-' to read from stdin (one per line).")
    p.add_argument("--json", action="store_true")
    p.add_argument("--fields", default="", metavar="FIELDS",
                   help="Comma-separated fields for TSV output: id,label,title,type,status,"
                        "level,scope,summary,domain,keywords,created,history.")

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
                   help="Search terms (matches title + label + body + keywords, case-insensitive).")
    p.add_argument("--or", dest="or_mode", action="store_true",
                   help="Combine multiple terms with OR instead of AND.")
    p.add_argument("--regex", default="", metavar="PATTERN",
                   help="Regex pattern applied to title + label + body (re.IGNORECASE).")
    p.add_argument("--type", default="", choices=VALID_TYPES_SORTED + [""])
    p.add_argument("--level", default="", choices=VALID_LEVELS_SORTED + [""])
    p.add_argument("--status", default="", choices=VALID_STATUSES_SORTED + [""])
    p.add_argument("--scope", default="")
    p.add_argument("--domain", default="")
    p.add_argument("--json", action="store_true")
    p.add_argument("--plain", action="store_true",
                   help="Plain id/label output instead of typed wiki-links.")
    p.add_argument("--fields", default="", metavar="FIELDS",
                   help="Comma-separated fields for TSV output: id,label,title,type,status,"
                        "level,scope,summary,domain,keywords,created,history.")
    p.add_argument("--count", action="store_true", help="Print result count only.")
    p.add_argument("--limit", type=int, default=None, metavar="N",
                   help="Show at most N results.")

    # --- ls ---
    p = sub.add_parser("ls", help="List all docs (optionally filter by type).")
    p.add_argument("--type", default="", choices=VALID_TYPES_SORTED + [""])
    p.add_argument("--json", action="store_true")
    p.add_argument("--plain", action="store_true",
                   help="Plain id/label output instead of typed wiki-links.")
    p.add_argument("--fields", default="", metavar="FIELDS",
                   help="Comma-separated fields for TSV output: id,label,title,type,status,"
                        "level,scope,summary,domain,keywords,created,history.")
    p.add_argument("--count", action="store_true", help="Print doc count only.")
    p.add_argument("--limit", type=int, default=None, metavar="N",
                   help="Show at most N results.")

    # --- orphans ---
    p = sub.add_parser(
        "orphans",
        help="List docs outside the belongs_to hierarchy (no belongs_to in OR out).",
    )
    p.add_argument("--json", action="store_true")
    p.add_argument("--plain", action="store_true",
                   help="Plain id/label output instead of typed wiki-links.")
    p.add_argument("--fields", default="", metavar="FIELDS",
                   help="Comma-separated fields for TSV output: id,label,title,type,status,"
                        "level,scope,summary,domain,keywords,created,history.")
    p.add_argument("--count", action="store_true", help="Print orphan count only.")
    p.add_argument("--limit", type=int, default=None, metavar="N",
                   help="Show at most N results.")

    # --- map ---
    p = sub.add_parser(
        "map",
        help="Orientation map: the store's entry points (signpost roots) with summaries.",
    )
    p.add_argument("--json", action="store_true")

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
                   choices=["requires", "belongs_to", "relates", "provenance",
                            "superseded_by", "required_by", "children",
                            "dependents", "provenance_of", "all"])
    p.add_argument("--json", action="store_true")
    p.add_argument("--plain", action="store_true",
                   help="Plain id/label edge format instead of typed wiki-links.")
    p.add_argument("--count", action="store_true",
                   help="Print neighbor count only (total edges in the requested --kind).")

    # --- graph ---
    p = sub.add_parser("graph", help="BFS traversal over hard edges (requires + belongs_to).")
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

    # --- domains ---
    p = sub.add_parser(
        "domains",
        help="Domain registry: list every distinct domain tag in use with doc counts.",
    )
    p.add_argument("--json", action="store_true",
                   help='Emit [{"domain": str, "count": int}, ...] in sort order.')
    p.add_argument("--plain", action="store_true",
                   help="One <count>\\t<domain> per line, no header.")

    # --- new ---
    p = sub.add_parser("new", help="Create a new doc.",
                       description=(
                           "Type-aware defaults:\n"
                           "  --level:  incidental (override with --level)\n"
                           "  --status: living     (override with --status)\n"
                           "  --label:  auto-derived as Title-Case from title words\n"
                           "            (up to ~24 chars, word boundaries only)\n"
                           "Edge refs validated before writing; unresolved refs cause an error."
                       ),
                       formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--type", required=True, choices=VALID_TYPES_SORTED)
    p.add_argument("--label", required=True,
                   help="Short (2–5 word) Title-Case handle. REQUIRED — the primary "
                        "human-meaningful name; must say what the doc is about, not a "
                        "fragment.")
    p.add_argument("--title", default="",
                   help="Optional sentence-length elaboration of the label. Defaults "
                        "to the label when omitted.")
    p.add_argument("--summary", default="",
                   help="2–5 sentence overview of the doc's concept (omitted if empty).")
    p.add_argument("--level", default="incidental", choices=VALID_LEVELS_SORTED)
    p.add_argument("--status", default="living", choices=VALID_STATUSES_SORTED)
    p.add_argument("--requires", default="",
                   help="Comma-separated ids/labels/titles. Cascade-hard. Validated before write.")
    p.add_argument("--belongs-to", "--parent", default="", dest="belongs_to",
                   help="Comma-separated ids/labels/titles. Cascade-hard (structural parent). "
                        "Validated before write.")
    p.add_argument("--relates", default="",
                   help="Comma-separated ids/labels/titles. Navigation/clustering. Validated before write.")
    p.add_argument("--provenance", default="",
                   help="Comma-separated ids/labels/titles. Immutable derivation lineage. Validated before write.")
    p.add_argument("--superseded-by", default="", dest="superseded_by",
                   help="Comma-separated ids/labels/titles. Deprecation pointer. Validated before write.")
    p.add_argument("--tags-domain", default="", dest="tags_domain")
    p.add_argument("--tags-keywords", default="", dest="tags_keywords",
                   help="Comma-separated findability keywords (flat list, replace semantics).")
    p.add_argument("--tags-scope", default="", dest="tags_scope")
    p.add_argument("--kind", default="", choices=REFERENCE_KIND_CHOICES + [""])
    p.add_argument("--source", default="")
    p.add_argument("--origin", default="",
                   help='reference docs: corpus/system of origin (e.g. "notion", "codebase:foo").')
    p.add_argument("--medium", default="",
                   help='reference docs: medium of the source (e.g. "pdf", "scan", "notion-page").')
    p.add_argument("--authored-at", dest="authored_at", default="",
                   help='reference docs: when the SOURCE was written, possibly fuzzy (e.g. "2024-03").')
    p.add_argument("--body", default="", help="Body text or '-' to read from stdin.")
    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="Preview what would be created without writing.")

    # --- set ---
    p = sub.add_parser("set", help="Update frontmatter fields or body of a doc.")
    p.add_argument("refs", nargs="+", metavar="ref",
                   help="id | label | title; or '-' to read from stdin (one per line).")
    p.add_argument("--title", default=None)
    p.add_argument("--summary", default=None,
                   help="Replace the summary scalar (empty string removes it).")
    p.add_argument("--label", default=None)
    p.add_argument("--level", default=None, choices=VALID_LEVELS_SORTED)
    p.add_argument("--status", default=None, choices=VALID_STATUSES_SORTED)
    p.add_argument("--type", default=None, choices=VALID_TYPES_SORTED)
    p.add_argument("--scope", default=None,
                   help="Single string naming a topological zone; applies to this "
                        "doc and its whole belongs_to subtree. Empty string clears it.")
    p.add_argument("--domain", default=None,
                   help="Comma-separated cross-cutting domain tags (flat list, NOT "
                        "inherited). Replaces the doc's domain list; empty string clears it.")
    p.add_argument("--keywords", default=None,
                   help="Comma-separated findability keywords (flat list, NOT inherited). "
                        "Replaces the doc's keywords list; empty string clears it.")
    p.add_argument("--body", default=None,
                   help="Replace body: TEXT value or '-' to read from stdin.")
    p.add_argument("--note", default="",
                   help="Add a history entry to each ref after updating.")
    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="Preview what would change without writing.")

    # --- edit ---
    p = sub.add_parser("edit",
                       help="Replace a doc's body from stdin (alias for: set <ref> --body -).")
    p.add_argument("ref", help="id | label | title")

    # --- link ---
    p = sub.add_parser("link", help="Add edge(s) to a doc.")
    p.add_argument("refs", nargs="+", metavar="ref",
                   help="id | label | title; or '-' to read from stdin (one per line).")
    p.add_argument("--requires", default="",
                   help="Comma-separated ids/labels/titles. Cascade-hard. Validated before write.")
    p.add_argument("--belongs-to", "--parent", default="", dest="belongs_to",
                   help="Comma-separated ids/labels/titles. Cascade-hard (structural parent). "
                        "Validated before write.")
    p.add_argument("--relates", default="",
                   help="Comma-separated ids/labels/titles. Navigation/clustering.")
    p.add_argument("--provenance", default="",
                   help="Comma-separated ids/labels/titles. Immutable derivation lineage.")
    p.add_argument("--superseded-by", default="", dest="superseded_by",
                   help="Comma-separated ids/labels/titles. Deprecation pointer.")
    p.add_argument("--replace", action="store_true",
                   help="Replace existing belongs_to edge(s) instead of adding. Only affects --belongs-to/--parent.")
    p.add_argument("--note", default="",
                   help="Add a history entry to each ref after linking.")
    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="Preview the edges that would be added without writing.")

    # --- unlink ---
    p = sub.add_parser("unlink", help="Remove edge(s) from a doc.")
    p.add_argument("refs", nargs="+", metavar="ref",
                   help="id | label | title; or '-' to read from stdin (one per line).")
    p.add_argument("--requires", default="",
                   help="Comma-separated ids/labels/titles.")
    p.add_argument("--belongs-to", "--parent", default="", dest="belongs_to",
                   help="Comma-separated ids/labels/titles.")
    p.add_argument("--relates", default="",
                   help="Comma-separated ids/labels/titles.")
    p.add_argument("--provenance", default="",
                   help="Comma-separated ids/labels/titles.")
    p.add_argument("--superseded-by", default="", dest="superseded_by",
                   help="Comma-separated ids/labels/titles.")
    p.add_argument("--note", default="",
                   help="Add a history entry to each ref after unlinking.")

    # --- history ---
    p = sub.add_parser("history", help="Add a history entry to a doc.")
    p.add_argument("refs", nargs="+", metavar="ref",
                   help="id | label | title; or '-' to read from stdin (one per line).")
    p.add_argument("--add", required=True, help="Summary text for the history entry.")

    # --- rm ---
    p = sub.add_parser(
        "rm",
        help="Delete a doc from the store and reindex. Blocked by inbound edges unless --force.",
    )
    p.add_argument("ref", help="id | label | title")
    p.add_argument(
        "--force",
        action="store_true",
        help="Strip all inbound edges (requires/belongs_to/relates/provenance/superseded_by) then delete.",
    )
    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="Preview what would be deleted without writing.")

    # --- ingest-raw ---
    p = sub.add_parser("ingest-raw", help="Write verbatim content into raw/ tier.")
    p.add_argument("--source", default="",
                   help="Where the content came from. Required unless --inherit-from supplies it.")
    p.add_argument("--from-file", default="", dest="from_file")
    p.add_argument("--body", default="")
    p.add_argument("--title", default="")
    p.add_argument("--label", default="")
    p.add_argument("--origin", default="",
                   help='Corpus/system the material came from (e.g. "notion", "codebase:foo").')
    p.add_argument("--medium", default="",
                   help='Medium of the source (e.g. "pdf", "scan", "notion-page").')
    p.add_argument("--authored-at", dest="authored_at", default="",
                   help='When the SOURCE was written, possibly fuzzy (e.g. "2024-03").')
    p.add_argument("--parent-raw", dest="parent_raw", default="",
                   help="Shard (gate 1.5): parent raw ref (id or 'raw/<id>.md') this slice was cut from.")
    p.add_argument("--inherit-from", dest="inherit_from", default="",
                   help="Shard (gate 1.5): copy origin/medium/authored_at/captured/source from this "
                        "parent raw and set parent_raw + shard_depth automatically.")
    p.add_argument("--shard-depth", dest="shard_depth", type=int, default=None,
                   help="Shard recursion depth; auto-derived from parent when --inherit-from is used.")

    # --- inbox ---
    p_inbox = sub.add_parser(
        "inbox",
        help="Inbox drop-point: instant capture before ingestion (gate 0).",
    )
    inbox_sub = p_inbox.add_subparsers(dest="inbox_verb", metavar="verb")
    inbox_sub.required = True

    p_ia = inbox_sub.add_parser(
        "add",
        help="Drop one item into the inbox verbatim (no processing).",
    )
    p_ia.add_argument("--from-file", default="", dest="from_file",
                      help="Read verbatim body from this file path.")
    p_ia.add_argument("--body", default="",
                      help="Inline body text; use '-' to read from stdin.")
    p_ia.add_argument("--title", default="",
                      help="Human-readable title (stored in frontmatter only).")
    p_ia.add_argument("--source", default="",
                      help="Where the content came from (URL, file, description).")
    p_ia.add_argument("--origin", default="",
                      help='Corpus/system the material came from (e.g. "notion", "codebase:foo").')
    p_ia.add_argument("--medium", default="",
                      help='Medium of the source (e.g. "pdf", "scan", "notion-page", "source-file").')
    p_ia.add_argument("--authored-at", dest="authored_at", default="",
                      help='When the SOURCE was written, possibly fuzzy (e.g. "2024-03", "circa 2023").')

    inbox_sub.add_parser("list", help="List items currently in the inbox.")

    # --- promote ---
    p = sub.add_parser(
        "promote",
        help="Gate 1: move inbox item(s) → raw/ with raw-clipping frontmatter. "
             "For raw→docs, use the ingest-reference skill (gate 2).",
    )
    p.add_argument("ref", nargs="?", default="",
                   help="id or unique substring of an inbox item.")
    p.add_argument("--all", action="store_true",
                   help="Promote (drain) every item currently in the inbox.")

    # --- raw ---
    p_raw = sub.add_parser(
        "raw",
        help="Raw tier: inspect ingest-state and mark items ingested (gate 2 bookkeeping).",
    )
    raw_sub = p_raw.add_subparsers(dest="raw_verb", metavar="verb")
    raw_sub.required = True
    p_rl = raw_sub.add_parser(
        "list",
        help="List raw items with ingest-state (ingested_at flag + graph cross-check).",
    )
    p_rl.add_argument("--pending", action="store_true",
                      help="Show only items not yet ingested (no flag AND no graph reference).")
    p_rs = raw_sub.add_parser(
        "show",
        help="Print a raw clipping's full content (frontmatter + verbatim body).",
    )
    p_rs.add_argument("ref", help="id or unique substring of a raw item.")
    p_rm = raw_sub.add_parser(
        "mark-ingested",
        help="Flag a raw item as ingested; ingest-reference calls this when decomposition completes.",
    )
    p_rm.add_argument("ref", help="id or unique substring of a raw item.")
    p_rc = raw_sub.add_parser(
        "children",
        help="List the child shards of a parent raw (gate 1.5), each with its ingest-state.",
    )
    p_rc.add_argument("ref", help="id or unique substring of a parent raw item.")

    # --- validate ---
    sub.add_parser("validate", help="Run structural integrity checks.")

    # --- reindex ---
    sub.add_parser("reindex", help="Rebuild docs/.index/ artifacts.")

    # --- viewer ---
    p = sub.add_parser(
        "viewer",
        help="Build the self-contained read-only HTML viewer (default: build/viewer.html).",
    )
    p.add_argument(
        "--out",
        default="",
        metavar="PATH",
        help="Output HTML path (default: <store-root>/build/viewer.html).",
    )

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
    p_rsg.add_argument("--as", dest="as_who", default=None,
                       help="Signature (git author format). Default: user.name + user.email from config.")

    # --- config (user preferences; no store required) ---
    # Minimal stub so `ldoc --help` lists the subcommand. Actual parsing is
    # handled by user_config._build_config_parser(), invoked in main() before
    # parse_args() so flag-like args (--list, --unset, etc.) reach it cleanly.
    sub.add_parser(
        "config",
        help="Read/write user preferences in ~/.config/live_docs/config.toml.",
        add_help=False,
    )

    # --- help ---
    sub.add_parser("help", help="Show overview with grouped verbs and copy-pasteable examples.")

    return parser


# ---------------------------------------------------------------------------
# Auto viewer rebuild
# ---------------------------------------------------------------------------

# Subcommands that mutate tiers exported into viewer.html (docs/, reviews/).
_VIEWER_MUTATING = frozenset({"new", "set", "edit", "link", "unlink", "history", "rm"})
_REVIEW_MUTATING = frozenset({"new", "sign"})


def _should_auto_rebuild_viewer(args, rc: int) -> bool:
    """True when a successful invocation changed viewer-visible store content."""
    if rc != 0:
        return False
    if getattr(args, "no_viewer", False):
        return False

    cmd = args.subcommand
    if cmd == "viewer":
        return False
    if cmd in _VIEWER_MUTATING:
        return not getattr(args, "dry_run", False)
    if cmd == "review":
        return getattr(args, "review_verb", None) in _REVIEW_MUTATING
    return False


def _maybe_auto_rebuild_viewer(args, rc: int) -> None:
    if not _should_auto_rebuild_viewer(args, rc):
        return
    from livedocs.viewer import auto_rebuild_viewer

    auto_rebuild_viewer()


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

COMMANDS = {
    "get": cmd_get,
    "body": cmd_body,
    "show": cmd_show,
    "find": cmd_find,
    "ls": cmd_ls,
    "orphans": cmd_orphans,
    "map": cmd_map,
    "resolve": cmd_resolve,
    "label": cmd_label,
    "neighbors": cmd_neighbors,
    "graph": cmd_graph,
    "log": cmd_log,
    "count": cmd_count,
    "domains": cmd_domains,
    "new": cmd_new,
    "set": cmd_set,
    "edit": cmd_edit,
    "link": cmd_link,
    "unlink": cmd_unlink,
    "history": cmd_history,
    "rm": cmd_rm,
    "ingest-raw": cmd_ingest_raw,
    "inbox": cmd_inbox,
    "promote": cmd_promote,
    "raw": cmd_raw,
    "validate": cmd_validate,
    "reindex": cmd_reindex,
    "viewer": cmd_viewer,
    "edges": cmd_edges,
    "review": cmd_review,
    "config": cmd_config,
    "help": cmd_help,
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    # `ldoc config` is store-free; argparse's subparser dispatch can't reliably
    # pass flag-like args (--list, --unset) through REMAINDER, so we route it
    # directly before parse_args(). This is safe now that the module-level
    # imports no longer trigger store discovery.
    if len(sys.argv) >= 2 and sys.argv[1] == "config":
        from livedocs.user_config import run_config_cli
        return run_config_cli(sys.argv[2:])

    parser = build_parser()
    args = parser.parse_args()

    handler = COMMANDS.get(args.subcommand)
    if not handler:
        _err(f"Unknown subcommand: {args.subcommand}")
        return 1

    if args.subcommand == "help":
        return handler(None, args)

    from livedocs import DOCS_DIR
    kb = KB(DOCS_DIR)
    rc = handler(kb, args)
    _maybe_auto_rebuild_viewer(args, rc)
    return rc


if __name__ == "__main__":
    sys.exit(main())
