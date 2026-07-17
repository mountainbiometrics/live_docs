"""
lexicon.py — Store-hosted lexical term records (sibling box, not the doc graph).

Terms live under a configurable lexicon/ box (default kb/lexicon/). Identity is
the term slug (plus optional context for homonyms) — not opaque timestamps.
References are soft wiki-links: broken links are allowed and are not rewritten
when a term is replaced under a new identity.

Record path:
    lexicon/<term>.md              — ubiquitous
    lexicon/<context>/<term>.md    — disambiguated sense

Explicit term links use ``{{…}}`` (separate from doc ``[[14-digit]]`` wikilinks):
    {{Cascade}}
    {{(Lexicon) Term}}
    {{Hard Edge}}s

Stdlib only. No external dependencies.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .serialize import _parse_frontmatter_text, _yaml_str

# Explicit term links: {{Cascade}}, {{(Lexicon) Term}}, {{lexicon/term}}
# Optional display alias: {{hard-edge|Hard Edges}}
# Plural / inflection suffix outside the braces: {{Hard Edge}}s → displays "Hard Edges"
TERM_LINK_RE = re.compile(
    r"\{\{"
    r"([^}|]+?)"           # target (display/path form)
    r"(?:\|([^}]*))?"      # optional |display
    r"\}\}"
    r"([A-Za-z]*)"         # trailing inflection (s, es, …)
)
DISPLAY_WITH_CONTEXT_RE = re.compile(
    r"^\(\s*([^)]+?)\s*\)\s+(.+)$"
)

# On-disk fields only — identity is the path; `id` is derived in memory, never written.
# No created/history — git is enough if anyone needs provenance of a term file.
TERM_FIELD_ORDER = (
    "term",
    "definition",
    "context",
    "allowed_aliases",
    "restricted_aliases",
    "similar_terms",
)

_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Lowercase kebab-case slug for term/context path segments."""
    s = (text or "").strip().lower().replace("_", "-").replace(" ", "-")
    s = _SLUG_STRIP_RE.sub("-", s)
    return s.strip("-")


def title_case_words(text: str) -> str:
    """Title-case words for display (keeps existing internal caps lightly)."""
    parts = re.split(r"(\s+|-)", (text or "").strip())
    out: list[str] = []
    for p in parts:
        if not p or p.isspace() or p == "-":
            out.append(p)
        elif p.isupper() and len(p) <= 3:
            out.append(p)  # acronym-ish
        else:
            out.append(p[:1].upper() + p[1:] if p else p)
    return "".join(out)


def term_id(term: str, context: str | None = None) -> str:
    """Return the stable path id: ``term`` or ``context/term`` (slugs)."""
    t = slugify(term)
    if not t:
        raise ValueError("term slug is empty")
    if context:
        c = slugify(context)
        if not c:
            raise ValueError("context slug is empty")
        return f"{c}/{t}"
    return t


def display_form(term: str, context: str | None = None) -> str:
    """Human display: ``Term`` or ``(Context) Term`` (Title Case)."""
    t = title_case_words(term)
    if context:
        return f"({title_case_words(context)}) {t}"
    return t


def parse_term_ref(inner: str) -> tuple[str | None, str]:
    """Parse a wiki-link inner into (context_or_None, term_text).

    Accepts:
      Cascade
      (Graph) Cascade
      graph/cascade
      cascade
    """
    raw = (inner or "").strip()
    if not raw:
        raise ValueError("empty term ref")
    if "/" in raw and not raw.startswith("("):
        # path form: context/term or bare term with slash only as delimiter
        left, _, right = raw.partition("/")
        if right and "/" not in right:
            return (left.strip() or None), right.strip()
        # nested/odd — treat whole as term path id; caller slugifies
        return None, raw
    m = DISPLAY_WITH_CONTEXT_RE.match(raw)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None, raw


def ref_to_id(inner: str) -> str:
    """Resolve a term-link inner (or bare display/path) to a term id."""
    ctx, term = parse_term_ref(inner)
    return term_id(term, ctx)


def iter_term_links(text: str) -> list[tuple[str, str, str]]:
    """Return [(full_token, target_inner, display_text), ...] for ``{{…}}`` term links."""
    out: list[tuple[str, str, str]] = []
    for m in TERM_LINK_RE.finditer(text or ""):
        target = m.group(1).strip()
        alias = (m.group(2) or "").strip()
        suffix = m.group(3) or ""
        display = (alias or target) + suffix
        out.append((m.group(0), target, display))
    return out


def parse_term(path: Path, lexicon_root: Path | None = None) -> dict[str, Any]:
    """Parse a term file into a dict. ``id`` is authoritative from relative path."""
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        fm: dict[str, Any] = {"body": text}
    else:
        fm = _parse_frontmatter_text(parts[1])
        fm["body"] = parts[2].lstrip("\n")

    root = lexicon_root or path.parent
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        rel = Path(path.name)
    tid = str(rel.with_suffix("")).replace("\\", "/")
    fm["id"] = tid

    # Derive context/term from path when frontmatter omits them
    if "/" in tid:
        ctx_slug, term_slug = tid.split("/", 1)
        fm.setdefault("context", title_case_words(ctx_slug.replace("-", " ")))
        fm.setdefault("term", title_case_words(term_slug.replace("-", " ")))
    else:
        fm.setdefault("term", title_case_words(tid.replace("-", " ")))

    for key in ("allowed_aliases", "restricted_aliases", "similar_terms"):
        val = fm.get(key)
        if val is None:
            continue
        if isinstance(val, list):
            fm[key] = [str(v) for v in val if v]
        else:
            fm[key] = [str(val)]

    return fm


def dump_term(term: dict[str, Any]) -> str:
    """Serialize a term record to on-disk markdown.

    Never emits ``id`` — the relative path under lexicon/ is the identity.
    """
    lines = ["---"]
    for key in TERM_FIELD_ORDER:
        if key not in term:
            continue
        val = term[key]
        if val is None:
            continue
        if key in ("allowed_aliases", "restricted_aliases", "similar_terms"):
            if not val:
                continue
            # Quote each item — aliases may contain spaces ("broken link").
            inner = ", ".join(_yaml_str(str(v)) for v in val)
            lines.append(f"{key}: [{inner}]")
            continue
        if key == "context" and not val:
            continue
        if isinstance(val, str):
            lines.append(f"{key}: {_yaml_str(val)}")
        else:
            lines.append(f"{key}: {_yaml_str(str(val))}")
    lines.append("---")
    body = (term.get("body") or "").strip()
    if body:
        lines.append("")
        lines.append(body)
        if not body.endswith("\n"):
            lines.append("")
    else:
        lines.append("")
    return "\n".join(lines) + ("\n" if not lines[-1].endswith("\n") else "")


class LexiconStore:
    """Query/mutation layer over the lexicon/ box."""

    def __init__(self, lexicon_dir: Path | None = None):
        if lexicon_dir is None:
            from .model import LEXICON_DIR

            lexicon_dir = LEXICON_DIR
        self.lexicon_dir = lexicon_dir

    def path_for(self, tid: str) -> Path:
        tid = tid.strip().replace("\\", "/").lstrip("/")
        if not tid or ".." in tid.split("/"):
            raise ValueError(f"invalid term id: {tid!r}")
        return self.lexicon_dir / f"{tid}.md"

    def ensure_dir(self) -> None:
        self.lexicon_dir.mkdir(parents=True, exist_ok=True)

    def all_paths(self) -> list[Path]:
        if not self.lexicon_dir.is_dir():
            return []
        return sorted(self.lexicon_dir.rglob("*.md"))

    def load_all(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for path in self.all_paths():
            rec = parse_term(path, self.lexicon_dir)
            out[rec["id"]] = rec
        return out

    def get(self, ref: str) -> dict:
        """Resolve by id, display form, or unique substring of term/id."""
        ref = (ref or "").strip()
        if not ref:
            raise ValueError("empty term ref")
        # Direct id / display / path
        try:
            tid = ref_to_id(ref)
        except ValueError:
            tid = slugify(ref)
        path = self.path_for(tid)
        if path.is_file():
            return parse_term(path, self.lexicon_dir)

        # Unique substring over id + term + aliases
        needle = ref.lower()
        matches: list[dict] = []
        for rec in self.load_all().values():
            hay = " ".join(
                [
                    rec.get("id", ""),
                    rec.get("term", ""),
                    rec.get("context") or "",
                    display_form(rec.get("term", ""), rec.get("context")),
                    " ".join(rec.get("allowed_aliases") or []),
                ]
            ).lower()
            if needle == rec.get("id", "").lower() or needle in hay:
                matches.append(rec)
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise ValueError(f"term not found: {ref!r}")
        ids = ", ".join(m["id"] for m in matches[:8])
        raise ValueError(f"ambiguous term ref {ref!r}: {ids}")

    def new(
        self,
        *,
        term: str,
        definition: str,
        context: str | None = None,
        allowed_aliases: list[str] | None = None,
        restricted_aliases: list[str] | None = None,
        similar_terms: list[str] | None = None,
        body: str = "",
    ) -> tuple[str, Path]:
        tid = term_id(term, context)
        path = self.path_for(tid)
        if path.exists():
            raise ValueError(f"term already exists: {tid}")
        self.ensure_dir()
        path.parent.mkdir(parents=True, exist_ok=True)

        # Canonical stored forms: keep caller spelling for term/context display.
        # Path is identity — do not persist `id` in frontmatter.
        term_disp = term.strip()
        ctx_disp = context.strip() if context else None
        rec: dict[str, Any] = {
            "term": term_disp,
            "definition": definition.strip(),
        }
        if ctx_disp:
            rec["context"] = ctx_disp
        if allowed_aliases:
            rec["allowed_aliases"] = list(allowed_aliases)
        if restricted_aliases:
            rec["restricted_aliases"] = list(restricted_aliases)
        if similar_terms:
            # normalize similar_terms to ids when possible
            normed = []
            for s in similar_terms:
                try:
                    normed.append(ref_to_id(s))
                except ValueError:
                    normed.append(s)
            rec["similar_terms"] = normed
        if body:
            rec["body"] = body
        path.write_text(dump_term(rec), encoding="utf-8")
        return tid, path

    def set(self, ref: str, **fields: Any) -> dict:
        rec = self.get(ref)
        tid = rec["id"]
        path = self.path_for(tid)

        # Identity fields: changing term/context = new identity (refuse in-place)
        if "term" in fields or "context" in fields:
            new_term = fields.get("term", rec.get("term"))
            new_ctx = fields.get("context", rec.get("context"))
            if new_ctx == "":
                new_ctx = None
            new_id = term_id(str(new_term), str(new_ctx) if new_ctx else None)
            if new_id != tid:
                raise ValueError(
                    f"term identity is the filename ({tid}); renaming would make a "
                    f"different term ({new_id}). Create the new term and leave the "
                    f"old id (broken links stay broken — language, not FK rewrites)."
                )

        for key in (
            "definition",
            "allowed_aliases",
            "restricted_aliases",
            "similar_terms",
            "body",
        ):
            if key not in fields:
                continue
            val = fields[key]
            if key in ("allowed_aliases", "restricted_aliases", "similar_terms"):
                if val is None or val == []:
                    rec.pop(key, None)
                else:
                    if key == "similar_terms":
                        normed = []
                        for s in val:
                            try:
                                normed.append(ref_to_id(str(s)))
                            except ValueError:
                                normed.append(str(s))
                        rec[key] = normed
                    else:
                        rec[key] = [str(v) for v in val]
            elif val is None or val == "":
                if key == "definition":
                    raise ValueError("definition cannot be empty")
                rec.pop(key, None)
            else:
                rec[key] = val

        path.write_text(dump_term(rec), encoding="utf-8")
        return parse_term(path, self.lexicon_dir)

    def rm(self, ref: str) -> str:
        rec = self.get(ref)
        tid = rec["id"]
        path = self.path_for(tid)
        path.unlink()
        # prune empty context directory
        parent = path.parent
        if parent != self.lexicon_dir and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
        return tid

    def find(self, query: str) -> list[dict]:
        q = (query or "").strip().lower()
        if not q:
            return list(self.load_all().values())
        hits = []
        for rec in self.load_all().values():
            blob = " ".join(
                [
                    rec.get("id", ""),
                    rec.get("term", ""),
                    rec.get("context") or "",
                    rec.get("definition") or "",
                    " ".join(rec.get("allowed_aliases") or []),
                    " ".join(rec.get("restricted_aliases") or []),
                    rec.get("body") or "",
                ]
            ).lower()
            if q in blob:
                hits.append(rec)
        return sorted(hits, key=lambda r: r.get("id", ""))

    def export_records(self) -> list[dict]:
        """JSON-friendly list for the viewer export."""
        records = []
        for rec in sorted(self.load_all().values(), key=lambda r: r["id"]):
            out = {
                "id": rec["id"],
                "term": rec.get("term", ""),
                "definition": rec.get("definition", ""),
                "display": display_form(rec.get("term", ""), rec.get("context")),
            }
            if rec.get("context"):
                out["context"] = rec["context"]
            for key in ("allowed_aliases", "restricted_aliases", "similar_terms"):
                if rec.get(key):
                    out[key] = list(rec[key])
            records.append(out)
        return records


def compute_term_stats(terms: list[dict], docs: list[dict]) -> dict[str, dict]:
    """Cheap usage stats: docs mentioning each term (explicit link or surface form).

    Returns map term_id -> {
      docs, by_type, by_domain, by_scope
    }
    """
    # Build match patterns per term: id, display, term, aliases (longest first)
    compiled: list[tuple[str, re.Pattern[str], set[str]]] = []
    for t in terms:
        tid = t["id"]
        surfaces: list[str] = [
            t.get("display") or display_form(t.get("term", ""), t.get("context")),
            t.get("term", ""),
            tid,
            tid.split("/")[-1],
        ]
        surfaces.extend(t.get("allowed_aliases") or [])
        surfaces.extend(t.get("restricted_aliases") or [])
        # unique, longest first
        seen: set[str] = set()
        ordered: list[str] = []
        for s in sorted((x for x in surfaces if x), key=len, reverse=True):
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(s)
        if not ordered:
            continue
        alts = "|".join(re.escape(s) for s in ordered)
        pat = re.compile(rf"(?i)(?<!\[\[)\b(?:{alts})\b")
        link_inners = {
            tid.lower(),
            (t.get("display") or "").lower(),
            (t.get("term") or "").lower(),
        }
        if t.get("context"):
            link_inners.add(
                display_form(t.get("term", ""), t.get("context")).lower()
            )
        compiled.append((tid, pat, link_inners))

    stats: dict[str, dict] = {
        tid: {"docs": 0, "by_type": {}, "by_domain": {}, "by_scope": {}}
        for tid, _, _ in compiled
    }

    for doc in docs:
        blob = " ".join(
            [
                str(doc.get("title") or ""),
                str(doc.get("summary") or ""),
                str(doc.get("body") or ""),
            ]
        )
        # explicit term links in this doc
        linked_ids: set[str] = set()
        for _tok, inner, _disp in iter_term_links(blob):
            try:
                linked_ids.add(ref_to_id(inner))
            except ValueError:
                pass

        dtype = str(doc.get("type") or "")
        dscope = str(doc.get("scope") or "")
        domains = doc.get("domain") or []
        if isinstance(domains, str):
            domains = [domains]

        for tid, pat, _inners in compiled:
            hit = tid in linked_ids or bool(pat.search(blob))
            if not hit:
                continue
            s = stats[tid]
            s["docs"] += 1
            if dtype:
                s["by_type"][dtype] = s["by_type"].get(dtype, 0) + 1
            if dscope:
                s["by_scope"][dscope] = s["by_scope"].get(dscope, 0) + 1
            for dom in domains:
                if dom:
                    s["by_domain"][str(dom)] = s["by_domain"].get(str(dom), 0) + 1

    return stats
