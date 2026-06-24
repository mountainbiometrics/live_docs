---
name: reference
user-invocable: true
description: >
  Canonical store-agnostic reference for working in ANY live_docs store: the
  ldoc CLI command surface, the frontmatter schema (field order, required
  fields, the three descriptors), the type/status/level enums, the typed edge
  model and cascade semantics, scope vs domain, and the all-metadata creation
  recipe. Read this FIRST when you land in a repo with a .live_docs.toml and
  need to read or write docs — it replaces rediscovering the system from
  `ldoc --help`. For WHICH skill to run for a given task, and the operating
  discipline, this points you on to the task skills (apply-to-docs, ingest-
  reference, revise-doc, garden, cascade-check, validate).
---

# reference — How to operate a live_docs store

You are in a repo with a `.live_docs.toml` marker. That means a **live_docs
store** is reachable: a flat graph of single-responsibility Markdown docs, read
and written only through the `ldoc` porcelain CLI. This doc is the portable
quick-reference so you don't have to reverse-engineer the system each session.

**The two rules that matter most:**

1. **All KB access goes through `ldoc`.** Never `cat`, `grep`, `jq`, or
   hand-edit doc files or frontmatter. The CLI is the only sanctioned reader and
   writer.
2. **Mutators are dumb; judgment lives in the skills.** `ldoc new/set/link` write
   exactly what you tell them and validate refs — they do NOT decide cascade,
   impact, or consistency. For any *substantive* change, run the matching skill
   (below), not raw `ldoc` calls.

---

## 0. Orient before you search

Don't start from a cold `ldoc find`. Get the map first:

```bash
ldoc map            # entry points (signpost roots) + their summaries, ranked
ldoc count          # how big the store is, by type/level/status
```

`ldoc map` prints the topological roots of the `belongs_to` hierarchy — the
biggest "signpost" docs first, each with its summary and its direct children.
That is your table of contents. From an entry point, follow edges
(`ldoc show <ref>`, `ldoc neighbors <ref>`) or search within scope
(`ldoc find ... --scope <zone>`).

---

## 1. The ldoc command surface

All ref arguments accept `id | label | title` (exact, or a unique
case-insensitive substring). Most read verbs take several refs; pass `-` as the
sole ref to read refs from stdin. Run `ldoc help` for the full banner, or
`ldoc <verb> --help` for one verb's flags. Most mutators accept `--dry-run`.

**Orient / search / read**

| Command | Purpose |
|---|---|
| `ldoc map [--json]` | Entry points (signpost roots) with summaries — start here |
| `ldoc find [terms] [--or] [--regex P] [--type] [--level] [--status] [--scope] [--domain] [--json]` | Full-text + faceted search (terms match title, label, body, keywords; facets filter by scope/domain only) |
| `ldoc ls [--type T] [--json]` | List docs (optionally one type) |
| `ldoc orphans` | Docs outside the belongs_to hierarchy |
| `ldoc domains [--json]` | List in-use domain tags with doc counts (the domain registry) |
| `ldoc count` / `ldoc log [--since ISO] [--limit N]` | Stats / recent-changes view |
| `ldoc get <ref...>` | Frontmatter summary |
| `ldoc show <ref...>` | Frontmatter + resolved edges + body |
| `ldoc body <ref...>` | Body only |
| `ldoc neighbors <ref> --kind requires\|belongs_to\|relates\|provenance\|superseded_by\|dependents\|provenance_of\|all` | Edges in/out |
| `ldoc graph <ref> [--depth N] [--direction up\|down\|both]` | BFS over cascade-hard edges |

**Mutate** (write only — pair with the skill that owns the judgment)

| Command | Purpose |
|---|---|
| `ldoc new --type T --label "..." [--title "..."] [options]` | Create a doc (`--label` required; `--title` optional, defaults to label) |
| `ldoc set <ref> [--title][--label][--summary][--level][--status][--type][--scope][--domain][--keywords][--body -\|TEXT]` | Update fields/body |
| `ldoc link <ref> [--requires\|--belongs-to\|--relates\|--provenance\|--superseded-by a,b]` | Add edges |
| `ldoc unlink <ref> [same edge flags]` | Remove edges |
| `ldoc history <ref> --add "what changed"` | Append a history entry (changes only — never creation) |

**Inbox pipeline & maintenance**

| Command | Purpose |
|---|---|
| `ldoc inbox add (--from-file P\|--body T\|-) [--title T] [--source S]` | Gate 0: capture verbatim, no processing |
| `ldoc inbox list` / `ldoc promote <ref> [--all]` | List / Gate 1: inbox → raw |
| `ldoc validate` | Read-only structural integrity check |
| `ldoc reindex` | Rebuild `<docs>/.index/` derived caches |
| `ldoc viewer [--out PATH]` | Build the read-only HTML viewer |
| `ldoc review new\|list\|show\|sign ...` | Post-hoc review ledger |

---

## 2. Frontmatter schema

### Canonical field order (the serializer enforces it — you don't hand-order)

```
id, title, label, summary, type, status, level,
belongs_to, requires, relates, provenance, superseded_by,
domain, keywords, scope, created, history
```

`keywords` — optional flat findability synonym list (same list shape as
`domain`, distinct purpose; not inherited, not cascade). Omitted when empty.

`reference`-type docs additionally carry `kind, source, imported` after
`history`.

### Required vs optional

**Required on every doc:** `id`, `title`, `label`, `type`, `status`, `level`,
`created`. Everything else is optional.

**Omit empty fields entirely.** Never write `[]`, never write an empty `scope:`
or `domain:` or `history:`. Absence == empty; the tooling treats them
identically. (`ldoc` already does this for you — this matters when you read.)

`id` is a 14-digit UTC timestamp that **equals the filename stem**. Never change
it; never rename files.

### The three descriptors

| Field | Format | Role |
|---|---|---|
| `label` | Title Case, 2–5 words | **Required** primary handle; names the subject; how `ldoc` resolves refs |
| `title` | Sentence-length phrase | Optional fuller name; elaborates the label, and defaults to it when omitted |
| `summary` | 1–3 sentences, ≤ ~50 words | The gist; mirrors the doc's opening line. Shown **verbatim** in `ldoc map`, search results, and review snapshots — keep it scannable |

`--label` is **required** on `ldoc new`; `--title` is optional and defaults to the label when omitted.

### Enums (these are the live values — `index` was retired)

```
type:   type | principle | goal | decision | constraint | requirement |
        use-case | guide | component | reference
status: living (current reality) | target (intended, not yet built) |
        deprecated (retired) | reference (frozen supporting material)
level:  incidental (calcified, no decision) | trial | preference | requirement
```

reference-type `kind`: `brainstorm | plan | clipping | external`.

Type-choice rule of thumb: prefer **`decision`** over `principle` when you're
describing HOW the system behaves; reserve `principle` for bedrock values.
(`identify-key-concepts` owns the full taxonomy protocol.)

---

## 3. Edge model

Edges are stored as quoted wikilinks (`["[[<id>]]"]`); `ldoc` unwraps them to
bare ids for you. There are five outbound edge types:

| Edge | Cascade | Use when |
|---|---|---|
| `requires` | **hard** | This doc is existentially dependent on the target — meaningless or wrong without it |
| `belongs_to` | **hard** | This doc is structurally a child of the target (part-of / membership). Drives the hierarchy AND scope inheritance |
| `relates` | soft | Symmetric see-also / topic kinship; not a dependency |
| `provenance` | soft | "Derived from / informed by"; may point at a raw clipping id |
| `superseded_by` | — | Required when `status: deprecated`; points at the replacement |

- **Cascade-hard edges** (`requires` + `belongs_to`) are what `cascade-check`
  walks and what the reverse-dependency map is built from. `relates` and
  `provenance` never cascade.
- **Reverse edges** (`dependents`, `provenance_of`) are generated by `reindex`.
  Never hand-author them.
- **A signpost is not a type.** Any doc that is the `belongs_to` target of other
  docs is structurally a navigational signpost (the retired `index` type,
  re-derived from topology). `ldoc map` surfaces them.

---

## 4. scope vs domain — two orthogonal facets

Both are optional tags, but they answer different questions and behave
differently:

| | `scope` | `domain` |
|---|---|---|
| Question | WHERE in the topology (which subsystem/zone) | WHICH business/problem area |
| Shape | single string | flat list of strings |
| Vocabulary | closed-ish (zone names) | open — any string; normalize to avoid drift |
| Inheritance | **inherited down `belongs_to`** | **NOT inherited** — set explicitly per doc |
| Effective value | union of `scope` along the whole belongs_to ancestry | exactly what's on the doc |

- Declare `scope` on **anchor docs** (structural roots of a subsystem). Leaf docs
  usually declare none and inherit. A doc that restates its parent's scope is
  redundant — garden flags it.
- Use `domain` only when a concern spans **two or more scopes**; a concern living
  entirely within one subsystem is already captured by that subsystem's scope.

**Setting them** (note the asymmetric flags):

```bash
# On creation:
ldoc new ... --tags-scope sinai --tags-domain "Ontology Mapping,Schema Evolution"
# On an existing doc:
ldoc set <ref> --scope sinai            # single string; "" clears it
ldoc set <ref> --domain "A,B Tag"       # comma list; "" clears it
# Search:
ldoc find --scope sinai --json
ldoc find --domain "Ontology Mapping"
```

---

## 5. Creating a doc with full metadata in one call

```bash
ldoc new \
  --type decision \
  --label "Short Noun Phrase" \
  --title "Sentence-length fuller name of the concept" \   # optional; defaults to label
  --summary "1–3 sentence gist that mirrors the doc's opening line." \
  --level preference \
  --status living \
  --belongs-to <signpost-ref> \
  --requires <dep-ref> \
  --relates <sibling-ref> \
  --provenance <raw-or-source-ref> \
  --tags-scope <zone> \
  --tags-domain "Area One,Area Two" \
  --body "The doc body. Use - to read from stdin." \
  --dry-run            # preview without writing; drop it to commit
```

`--label` is **required** — a 2–5 word Title-Case noun phrase naming the subject. `--title` is optional and defaults to the label. Edge refs accept id | label | title and are validated before anything is written. Membership points UP: the child declares `--belongs-to <parent>`, never the reverse.

---

## 6. Don't substitute raw ldoc for the skills

`ldoc` mutators carry no judgment. For substantive work, run the skill that owns
the procedure — it handles concept extraction, blast-radius, cascade, history,
and the post-hoc review summary:

| You want to… | Run |
|---|---|
| Land a request / design / plan into the KB | **apply-to-docs** |
| Bring in external material (notes, RFC, URL, research) | **ingest-reference** |
| Edit / correct / amend an existing doc | **revise-doc** |
| Record decisions already built in a working session | **reconcile-changes** |
| Know what else went stale after a change | **cascade-check** |
| Tidy navigation, orphans, grouping, tree structure | **garden** (or `/garden find homes for orphans`) |
| Refresh a signpost orientation guide | **garden** or **summarize-descendants** (alias → garden-summarize) |
| Periodic cleanup, decomposition, drift repair | **garden** |
| Structural integrity report (no fixes) | **validate** |
| Rebuild `.index/` caches | **reindex** |

When the plugin is installed, these are namespaced `/livedocs:<skill>`.

Deprecation is a protocol, not a flag flip: add a `## Correction` section, set
`--superseded-by`, then `--status deprecated`, then a history entry — or just let
**revise-doc** handle it. After any batch of writes, run `ldoc validate`.
