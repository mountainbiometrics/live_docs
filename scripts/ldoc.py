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
        [--kind requires|belongs_to|relates|provenance|superseded_by|dependents|provenance_of|all]
        [--json]

  ── Search / list ──
    find [term ...] [--or] [--regex PAT]
         [--type] [--level] [--status] [--scope] [--domain] [--json] [--plain]
    ls [--type] [--json] [--plain]
    log [--since <ISO>] [--limit N] [--json]
    count [--json]

  ── Graph ──
    graph <ref> [--depth N] [--direction up|down|both] [--json]
    edges [--json]

  ── Mutations ──
    new --type T --title T [--label L] [--level L] [--status S]
        [--requires a,b] [--belongs-to a,b] [--relates a,b]
        [--provenance a,b] [--superseded-by a,b]
        [--tags-domain d] [--tags-scope s]
        [--kind K] [--source S] [--body T|-] [--dry-run]
    set <ref> [--title] [--label] [--level] [--status] [--type]
              [--body -|TEXT] [--dry-run]
    edit <ref>   (alias: set <ref> --body -)
    link <ref> [--requires a,b] [--belongs-to a,b] [--relates a,b]
               [--provenance a,b] [--superseded-by a,b] [--dry-run]
    unlink <ref> [--requires a,b] [--belongs-to a,b] [--relates a,b]
                 [--provenance a,b] [--superseded-by a,b]
    history <ref> --add "summary"
    ingest-raw (--from-file P | --body T|-) --source S [--title T] [--label L]

  ── Inbox pipeline ──
    inbox add (--from-file P | --body T|-) [--title T] [--source S]
    inbox list
    promote <ref> [--all]

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

from livedocs import KB, DOCS_DIR, LABEL_RE, VALID_TYPES, VALID_LEVELS, VALID_STATUSES, VALID_REFERENCE_KINDS
from livedocs import ReviewLedger, REVIEWS_DIR
from livedocs import INBOX_DIR, RAW_DIR, generate_id


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
        summary = fm.get("summary", "")
        if summary:
            print(f"summary: {summary}")
        print(f"type:   {fm.get('type', '')}")
        print(f"status: {fm.get('status', '')}  level: {fm.get('level', '')}")
        print(f"created: {fm.get('created', '')}")
        print(f"domain: {fm.get('domain', [])}  scope: {fm.get('scope', [])}")
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
        print(f"  domain: {fm.get('domain',[])}  scope: {fm.get('scope',[])}")
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
        print("DEPENDENTS:")
        print(_fmt_edge_list(result["dependents"], plain=plain))
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


def cmd_new(kb: KB, args) -> int:
    edges = _parse_edge_args(args)
    domain_tags = [s.strip() for s in args.tags_domain.split(",") if s.strip()] \
        if args.tags_domain else []
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
        from livedocs.model import title_to_label, unique_label
        label = args.label or ""
        if not label:
            existing = (d.get("label", "") for d in kb._docs.values())
            label = unique_label(title_to_label(args.title), existing)
        print("## DRY RUN — would create:\n")
        print(f"  type:    {args.type}")
        print(f"  title:   {args.title}")
        print(f"  label:   {label}")
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
            title=args.title,
            label=args.label or "",
            summary=args.summary or "",
            level=args.level,
            status=args.status,
            **edges,
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
    if args.summary is not None:
        fields["summary"] = args.summary
    if args.label is not None:
        label = args.label.strip()
        if not LABEL_RE.match(label):
            _err(f"Invalid label: {args.label!r}. Must match "
                 f"^[A-Za-z0-9]+([ -][A-Za-z0-9]+)*$ (letters/digits, single spaces or hyphens).")
            return 1
        fields["label"] = label
    if args.level is not None:
        fields["level"] = args.level
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
        _err("No fields specified. Use --title, --label, --summary, --level, --status, --type, or --body.")
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


def _parse_edge_args(args) -> dict:
    """Parse all edge CLI args into lists of ref strings."""
    def _split(val: str) -> list:
        return [s.strip() for s in val.split(",") if s.strip()] if val else []
    return {
        "requires": _split(getattr(args, "requires", "") or ""),
        "belongs_to": _split(getattr(args, "belongs_to", "") or ""),
        "relates": _split(getattr(args, "relates", "") or ""),
        "provenance": _split(getattr(args, "provenance", "") or ""),
        "superseded_by": _split(getattr(args, "superseded_by", "") or ""),
    }


def cmd_link(kb: KB, args) -> int:
    edges = _parse_edge_args(args)

    if not any(edges.values()):
        _err("Specify at least one of: --requires, --belongs-to, --relates, "
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

    # --dry-run preview
    if getattr(args, "dry_run", False):
        print("## DRY RUN — would link:\n")
        for field, refs in edges.items():
            if refs:
                print(f"  --{field.replace('_', '-')}: {refs}")
        print("\n(No doc written.)")
        return 0

    try:
        kb.link(args.ref, **{k: v or None for k, v in edges.items()})
    except ValueError as e:
        _err(str(e))
        return 1

    print(f"Linked {args.ref}")
    return 0


def cmd_unlink(kb: KB, args) -> int:
    edges = _parse_edge_args(args)

    if not any(edges.values()):
        _err("Specify at least one of: --requires, --belongs-to, --relates, "
             "--provenance, --superseded-by.")
        return 1

    try:
        kb.unlink(args.ref, **{k: v or None for k, v in edges.items()})
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
    import re as _re

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
    pattern = _re.compile(_re.escape(ref), _re.IGNORECASE)
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

    lines = ["---", f"id: {_yaml_str_inbox(inbox_id)}"]
    if title:
        lines.append(f"title: {_yaml_str_inbox(title)}")
    lines.append("status: inbox")
    if source:
        lines.append(f"source: {_yaml_str_inbox(source)}")
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
        title = _read_frontmatter_field(p, "title")
        source = _read_frontmatter_field(p, "source")
        captured = _read_frontmatter_field(p, "captured")
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

    # Pull useful fields from inbox frontmatter
    original_source = _read_frontmatter_field(inbox_path, "source") or "(promoted from inbox)"
    title = _read_frontmatter_field(inbox_path, "title") or ""

    # Generate a collision-safe id for the raw tier
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_id = generate_id(RAW_DIR)

    imported = datetime.now(_tz.utc).strftime("%Y-%m-%d")

    # Build raw-clipping frontmatter (matches ingest_raw.py format exactly)
    fm_lines = ["---", f'id: "{raw_id}"']
    if title:
        fm_lines.append(f'title: "{title.replace(chr(34), chr(92)+chr(34))}"')
    fm_lines += [
        "type: reference",
        "kind: clipping",
        "status: historical",
        f'original_source: "{original_source.replace(chr(34), chr(92)+chr(34))}"',
        f'imported: "{imported}"',
        "---",
    ]
    frontmatter = "\n".join(fm_lines)

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

    body = ledger.render_body(rec.get("body", "")).strip()
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
  ldoc neighbors porcelain-roadmap --kind requires
  ldoc neighbors porcelain-roadmap --kind dependents
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
       --requires cognitive-load
  ldoc new --type decision --title "Test" --dry-run
  ldoc set porcelain-roadmap --title "New Title"
  ldoc set porcelain-roadmap --body -         # read body from stdin
  echo "new body text" | ldoc edit porcelain-roadmap
  ldoc link porcelain-roadmap --requires batch-operations
  ldoc link porcelain-roadmap --relates batch-operations --dry-run
  ldoc unlink porcelain-roadmap --requires batch-operations
  ldoc history porcelain-roadmap --add "Updated approach"

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
                   choices=["requires", "belongs_to", "relates", "provenance",
                            "superseded_by", "dependents", "provenance_of", "all"])
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
    p.add_argument("--summary", default="",
                   help="2–5 sentence overview of the doc's concept (omitted if empty).")
    p.add_argument("--level", default="incidental", choices=VALID_LEVELS_SORTED)
    p.add_argument("--status", default="living", choices=VALID_STATUSES_SORTED)
    p.add_argument("--requires", default="",
                   help="Comma-separated ids/labels/titles. Cascade-hard. Validated before write.")
    p.add_argument("--belongs-to", default="", dest="belongs_to",
                   help="Comma-separated ids/labels/titles. Cascade-hard (structural parent). "
                        "Validated before write.")
    p.add_argument("--relates", default="",
                   help="Comma-separated ids/labels/titles. Navigation/clustering. Validated before write.")
    p.add_argument("--provenance", default="",
                   help="Comma-separated ids/labels/titles. Immutable derivation lineage. Validated before write.")
    p.add_argument("--superseded-by", default="", dest="superseded_by",
                   help="Comma-separated ids/labels/titles. Deprecation pointer. Validated before write.")
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
    p.add_argument("--summary", default=None,
                   help="Replace the summary scalar (empty string removes it).")
    p.add_argument("--label", default=None)
    p.add_argument("--level", default=None, choices=VALID_LEVELS_SORTED)
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
    p.add_argument("--requires", default="",
                   help="Comma-separated ids/labels/titles. Cascade-hard. Validated before write.")
    p.add_argument("--belongs-to", default="", dest="belongs_to",
                   help="Comma-separated ids/labels/titles. Cascade-hard (structural parent). "
                        "Validated before write.")
    p.add_argument("--relates", default="",
                   help="Comma-separated ids/labels/titles. Navigation/clustering.")
    p.add_argument("--provenance", default="",
                   help="Comma-separated ids/labels/titles. Immutable derivation lineage.")
    p.add_argument("--superseded-by", default="", dest="superseded_by",
                   help="Comma-separated ids/labels/titles. Deprecation pointer.")
    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="Preview the edges that would be added without writing.")

    # --- unlink ---
    p = sub.add_parser("unlink", help="Remove edge(s) from a doc.")
    p.add_argument("ref", help="id | label | title")
    p.add_argument("--requires", default="",
                   help="Comma-separated ids/labels/titles.")
    p.add_argument("--belongs-to", default="", dest="belongs_to",
                   help="Comma-separated ids/labels/titles.")
    p.add_argument("--relates", default="",
                   help="Comma-separated ids/labels/titles.")
    p.add_argument("--provenance", default="",
                   help="Comma-separated ids/labels/titles.")
    p.add_argument("--superseded-by", default="", dest="superseded_by",
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
    "inbox": cmd_inbox,
    "promote": cmd_promote,
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
