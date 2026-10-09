---
name: reference
user-invocable: true
description: >
  Canonical store-agnostic reference for working in ANY live_docs store: the
  ldoc CLI command surface, the frontmatter schema (field order, required
  fields, the three descriptors), the type/status enums and the facets, the typed edge
  model and cascade semantics, scope vs domain, and the all-metadata creation
  recipe. Read this FIRST when you land in a repo with a .live_docs.toml and
  need to read or write docs — it replaces rediscovering the system from
  `ldoc --help`. For WHICH skill to run for a given task, and the operating
  discipline, this points you on to the task skills (apply-to-docs, ingest-
  reference, revise-doc, garden, cascade-check, validate). Also read it
  whenever you consult, search, quote, or cite a live_docs store while working
  on something else — answering a question, planning code, reviewing a change:
  it says how to read a doc line, what a doc claims, how to cite a doc, and how
  to flag a badly written one.
---

# reference — How to operate a live_docs store

You are in a repo with a `.live_docs.toml` marker. That means a **live_docs
store** is reachable: a flat graph of single-responsibility Markdown docs, read
and written only through the `ldoc` porcelain CLI. This doc is the portable
quick-reference so you don't have to reverse-engineer the system each session.

**The two rules that matter most:**

1. **Operate the store through `ldoc`.** Reading, searching, and mutating docs —
   frontmatter, edges, body — should all be reachable via the CLI. If you find
   yourself about to use `cat`, `grep`, `jq`, hand-edits, or similar for a store
   operation, check whether `ldoc` already covers it. When it doesn't, that may
   mean you're working around the system (and its validation), or it may mean the
   CLI still needs that capability — both are plausible; prefer `ldoc` when it
   can do the job.
2. **Mutators are dumb; judgment lives in the skills.** `ldoc new/set/link/rm`
   write exactly what you tell them and validate refs — they do NOT decide
   cascade, impact, or consistency. For any *substantive* change, run the
   matching skill (below), not raw `ldoc` calls.

---

## 0. Orient before you search

Don't start from a cold `ldoc find`. Get the map first:

```bash
ldoc map            # entry points (signpost roots) + their summaries, ranked
ldoc count          # how big the store is, by type, status, and facet
```

Every doc line on every surface reads `<Intent> <type>: <Title>` followed by
force and realization tags — e.g. "Requested decision: …", "Incidental
component: …" — and lists rank by status, then intent (requested, chosen,
then incidental). A missing intent is shown as Unattributed and weighs as
incidental. The first word says how much the person stood behind the claim;
it is context for the next change, not a lock. How a change's intent compares
with a doc's is `.claude/skills/_shared/facets.md`.

`ldoc map` prints the topological roots of the `belongs_to` hierarchy — the
biggest "signpost" docs first, each with its summary and its direct children.
That is your table of contents. From an entry point, follow edges
(`ldoc show <ref>`, `ldoc neighbors <ref>`) or search within scope
(`ldoc find ... --scope <zone>`).

**Reference/archived docs are demoted.** Docs with `type: reference` or
`status: reference` are footnote-grade snapshots, not current claims. By
default `ldoc map`, `ldoc ls`, `ldoc orphans`, and `ldoc validate` omit them;
`ldoc find` still matches them but ranks them last. Pass `--include-reference`
when you deliberately want the archive (validate's flag is opt-in because
archive-link hygiene is **not** a requirement). Reference snapshots are
immutable via porcelain — do not `set`/`history`/non-provenance-`link` them;
delete and re-ingest if wrong.

---

## 1. Reading and citing the store mid-task

These rules are for an agent that reads or cites the store while its task lies
elsewhere. They hold whatever the task, because a report built on a misread doc
passes the misreading to the person who acts on it.

**Read the doc line before the body.** The doc line is `<Intent> <type>:
<Title>` with force and realization tags. The facets, not the body, say whether
and how far a doc binds (`.claude/skills/_shared/facets.md`). An `incidental`
doc records an agent's proposal or a stop-gap; never present it as the person's
decision.

**A doc's claim is its title and summary.** When you report what a doc decides,
records, or requires, quote or paraphrase its title or summary. When only a
body sentence supports your statement, say that it is one sentence in the
doc's body, because body sentences drift from the claim the doc is about.

**Cite with `ldoc cite <ref>`.** It prints the doc line linked to the viewer.
Name every doc in a report or in chat this way, so the reader sees the facets
and can open the doc. Never name a doc by a phrase of your own, and never by
its id alone in prose. Every report template in these skills uses this form,
`[<Intent> <type>: <Title>](<url>)`, with ` · <force>` or ` · <realization>`
trailing where the template needs a tag.

**Whether a claim is built is `realization`.** A body sentence saying something
exists, or does not exist yet, goes stale without anyone editing the doc. Treat
it as `unassessed` and check the code.

**A `find` hit in the body is a mention.** `ldoc find` matches substrings in
title, label, and body, and each snippet names the field it came from
(`title:`, `body:`, ...). Search with the vocabulary of the mechanism that
exists as well as the vocabulary of the change you are proposing, and walk
`ldoc neighbors` of each hit before concluding what the store says.

**A doc that records the current design does not conflict with a new
request.** It becomes stale when the request lands. Report what is stale and
what the fix is; never hand the person a question the facets already answer.
The full rule is `.claude/skills/_shared/conflict-test.md`.

**Code and docs answer different questions.** The code says what the system
does; the docs say why. Neither outranks the other. Report a disagreement
between them as a finding, naming the cited doc and the code location.

**Flag a badly written doc and return to your task.** Run `ldoc flag add <ref>
--reason "<the sign you saw>"`. Do not rewrite the doc mid-task: a rewrite is a
governed change (revise-doc), and `/garden` drains open flags. The endpoint
writes nothing, so with no checkout of the store, name the doc and the sign you
saw in your report instead. The signs:

- not atomic: several claims, or a body past its type's ceiling
  (`.claude/skills/_shared/doc-types.md`);
- implementation state in a why doc;
- deferral or "not yet" language;
- negative-space language, stating what the thing is not;
- a body shaped like a changelog: update or correction paragraphs appended
  under an opening that is now false;
- a title that states a thesis instead of naming a topic.

**Write nothing else unasked.** The flag is the one write a reader makes. Any
other change waits until the person asks for it, and then runs through the
matching skill (§7).

---

## 2. The ldoc command surface

All ref arguments accept `id | label | title` (exact, or a unique
case-insensitive substring). Most read verbs take several refs; pass `-` as the
sole ref to read refs from stdin. Run `ldoc help` for the full banner, or
`ldoc <verb> --help` for one verb's flags. Most mutators accept `--dry-run`.

**Orient / search / read**

| Command | Purpose |
|---|---|
| `ldoc map [--include-reference] [--json]` | Entry points (signpost roots) with summaries — start here; omits reference/archived by default |
| `ldoc find [terms] [--or] [--regex P] [--type] [--status] [--intent] [--force] [--realization] [--imposed-by] [--scope] [--domain] [--json]` | Full-text + faceted search; reference/archived hits ranked last. `--intent incidental` is the ratification queue; `--realization planned` is the build backlog |
| `ldoc ls [--type T] [--include-reference] [--json]` | List docs (optionally one type); omits reference/archived by default |
| `ldoc orphans [--include-reference]` | Docs outside the belongs_to hierarchy (reference/archived omitted by default) |
| `ldoc domains [--json]` | List in-use domain tags with doc counts (the domain registry) |
| `ldoc count` / `ldoc log [--since ISO] [--limit N]` | Stats (tallies by type, status, and each facet) / recent-changes view |
| `ldoc get <ref...>` | Frontmatter summary, including `intent_basis` and `imposed_by` |
| `ldoc show <ref...>` | Frontmatter + resolved edges + body |
| `ldoc body <ref...>` | Body only |
| `ldoc neighbors <ref> --kind requires\|belongs_to\|relates\|provenance\|superseded_by\|dependents\|provenance_of\|all` | Edges in/out |
| `ldoc graph <ref> [--depth N] [--direction up\|down\|both]` | BFS over cascade-hard edges |
| `ldoc cite <ref>` | The doc line linked to the viewer: `[<Intent> <type>: <Title>](file://<viewer>#/<id>)`. The form for naming a doc in a report or chat |

**Mutate** (write only — pair with the skill that owns the judgment)

| Command | Purpose |
|---|---|
| `ldoc new --type T --label "..." [--title "..."] [options]` | Create a doc (`--label` required; `--title` optional, defaults to label). Refuses a doc that breaks the type's facet rules — a missing required facet, a forbidden one, or `--intent requested\|chosen` without `--intent-basis` |
| `ldoc set <ref> [--title][--label][--summary][--status][--type][--intent][--intent-basis][--force][--realization][--realization-refs a,b][--realization-verified][--imposed-by][--scope][--domain][--body -\|TEXT]` | Update fields/body (refused on reference/archived snapshots) |
| `ldoc link <ref> [--requires\|--belongs-to\|--relates\|--provenance\|--superseded-by a,b]` | Add edges (on reference/archived: provenance repair only) |
| `ldoc unlink <ref> [same edge flags]` | Remove edges; accepts literal 14-digit dead ids as edge targets (on reference/archived: provenance repair only) |
| `<mutate> ... --note "why"` | Explain a change inline — **preferred over `ldoc history`**. Auto-filled for obvious ops (new/re-parent/unlink/rm); required for a revision (body/label/title/summary), enforced at `session close` |
| `ldoc history <ref> --add "what changed"` | **Deprecated** post-hoc gap-filler for `--note` — use only to satisfy a close-gate after the fact (creation is now recorded in history); refused on reference/archived |
| `ldoc rm <ref> [--force] [--dry-run]` | Delete a doc; blocked when any inbound edge exists unless `--force` (strips all inbound edges then deletes); reindexes automatically. Allowed for reference/archived snapshots. |

> **Every mutation runs inside an editing session** (`ldoc session start` → work → `ldoc session close`), which stamps each change and mints the review. Read `.claude/skills/_shared/session-lifecycle.md` for the recipe.

**Inbox pipeline & maintenance**

| Command | Purpose |
|---|---|
| `ldoc inbox add (--from-file P\|--body T\|-) [--title T] [--source S]` | Gate 0: capture verbatim, no processing |
| `ldoc inbox list` / `ldoc promote <ref> [--all]` | List / Gate 1: inbox → raw |
| `ldoc validate [--include-reference]` | Structural integrity on the non-reference corpus by default; `--include-reference` opts into archive checks (not a requirement). Warns on bodies past their type's ceiling; ends with the open-flag count |
| `ldoc flag add <ref> --reason "..."` | Mark a badly written doc for gardening; the doc line gains ` · flagged` and `ldoc map` ends with the open-flag count |
| `ldoc flag list [--all] [--doc <ref>]` / `ldoc flag resolve <id> --note "..."` | Open flags (`--all` adds resolved ones) / close a flag with what was done to the doc, or the standard it meets when the flag was mistaken |
| `ldoc reindex` | Rebuild `<docs>/.index/` derived caches |
| `ldoc viewer [--out PATH]` | Build the read-only HTML viewer (default path: `[viewer] build_path`, else `build/viewer.html`) |
| `ldoc session start\|close\|list\|summary\|resume\|merge ...` | Editing-session lifecycle; every mutation runs in a session, `close` mints one review (see `.claude/skills/_shared/session-lifecycle.md`) |
| `ldoc review new\|list\|show\|sign ...` | Post-hoc review ledger (a review is minted at `session close`) |
| `ldoc store register <path> \| <name> --url URL [--remote-name N]` | Bind a store name to a location on this machine: a local checkout, or the url of a host that serves it. `--force` re-points an existing binding |
| `ldoc store list` / `ldoc store forget <name>` | Show each name's location / drop a binding |

**A store registered to a url is read-only from here.** Every read command
above works against it — `ldoc` resolves the url by calling the host's MCP
endpoint and prints exactly what it prints for a checkout, `--json` included.
Anything that would change the store (every mutator, `session`, `review
new/sign`, `term new/set/rm`, `validate`, `reindex`, `viewer`, the inbox and
raw pipeline) fails loud with exit 2 and says so; check the store out and
register its root, or run the command where the store lives. Set
`LIVEDOCS_MCP_TOKEN` when the host requires a token.

---

## 3. Frontmatter schema

### Canonical field order (the serializer enforces it — you don't hand-order)

```
id, title, label, summary, type, status,
intent, intent_basis, force, realization, realization_refs,
realization_verified, imposed_by,
belongs_to, requires, relates, provenance, superseded_by,
domain, scope, created, history
```

`domain` — optional flat governed business-grouping facet (not inherited, not
cascade). Omitted when empty. Docs are also findable by full-text search over
title, label, and body.

`reference`-type docs additionally carry `kind, source, imported` after
`history`.

### Required vs optional

**Required on every doc:** `id`, `title`, `label`, `type`, `status`,
`created`, and `intent` on every type except `reference`. Which of `force`,
`realization`, and `imposed_by` a doc must, may, or must not carry depends on
its type — the table in **`.claude/skills/_shared/doc-types.md`**.
`intent_basis` is required when `intent` is `requested` or `chosen`.
Everything else is optional.

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
        use-case | guide | component | heading | reference
status:       living | deprecated | reference
intent:       requested | chosen | incidental
force:        must | should | may
realization:  realized | partial | planned | deferred | unassessed
imposed_by:   environment | tradeoff | choice
```

`intent_basis` is a string (the quote or citation); `realization_refs` is a
list of anchors (paths, symbols, URLs); `realization_verified` is a date or
commit. What each value means and what it permits an agent to do:
**`.claude/skills/_shared/facets.md`**. `level` and `status: target` are
retired; `ldoc validate` warns when it finds them.

reference-type `kind`: `brainstorm | plan | clipping | external`.

### Type-choice — pick the most specific, don't default to `decision`

Almost anything can be framed as a "decision"; if you reach for it by default the
taxonomy collapses (it is already this store's most over-applied type). Ask
**"what is this *most*?"** and pick the most specific:

- `principle` bedrock value guiding many choices · `decision` one architectural
  choice among alternatives (scope it) · `constraint` a limit that must not be
  crossed · `requirement` property that must hold · `goal` outcome we're moving
  toward · `use-case` workflow/scenario served · `component` a thing that exists
  (module / boundary / contract) · `heading` a claimless parent over its
  children (a signpost may still be any type) · `guide` how to do or think · `reference`
  frozen source material · `type` defines a type (meta).

Before typing anything `decision`: if it just says a thing *exists* →
`component`; if it's *how to work* → `guide`; if it *bounds what may be done* → `constraint`; if it *must hold* → `requirement`/`goal`. Use `decision` only for a
real choice among alternatives with a rationale — then **scope it** under the
subtree it binds (no `belongs_to` = global, which is right only for genuinely
cross-cutting decisions).

The full classification ladder, the typing test, the per-type facet table, and
the why-chain are **`.claude/skills/_shared/doc-types.md`** — the source
`identify-key-concepts` and gardening apply.

---

## 4. Edge model

Edges are stored as quoted wikilinks (`["[[<id>]]"]`); `ldoc` unwraps them to
bare ids for you. There are five outbound edge types:

| Edge | Cascade | Use when |
|---|---|---|
| `requires` | **hard** | This doc is existentially dependent on the target — meaningless or wrong without it |
| `belongs_to` | **hard** | This doc is structurally a child of the target (part-of / membership). Drives the hierarchy AND scope inheritance |
| `relates` | soft | Symmetric see-also / topic kinship; not a dependency |
| `provenance` | soft | "Derived from / informed by"; may point at a raw clipping id |
| `superseded_by` | — | Required when `status: deprecated`; points at the replacement. Allowed on a `living` doc to point at its planned successor |

- **Cascade-hard edges** (`requires` + `belongs_to`) are what `cascade-check`
  walks and what the reverse-dependency map is built from. `relates` and
  `provenance` never cascade.
- **Reverse edges** (`dependents`, `provenance_of`) are generated by `reindex`.
  Never hand-author them.
- **A signpost is not a type.** Any doc that is the `belongs_to` target of other
  docs is structurally a navigational signpost (the retired `index` type,
  re-derived from topology). `ldoc map` surfaces them.

**What the hierarchy means.** `belongs_to` is the system's **mental model**, not a
mirror of the code's file tree — it *generally* matches code structure but is a
hybrid shaped by how the system actually hangs together (the docs explain the
system, not just the codebase). A doc's placement sets what it **binds**: a
decision under a subtree binds that subtree; no `belongs_to` = global. Keep the
tree **roughly balanced** — width proportional to depth — so navigation trades
breadth-at-a-glance against depth-to-detail. Operative placement rules + sizing:
**`.claude/skills/_shared/belongs-to-placement.md`**.

---

## 5. scope vs domain — two orthogonal facets

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
ldoc new ... --tags-scope <zone> --tags-domain "Area One,Area Two"
# On an existing doc:
ldoc set <ref> --scope <zone>           # single string; "" clears it
ldoc set <ref> --domain "A,B Tag"       # comma list; "" clears it
# Search:
ldoc find --scope <zone> --json
ldoc find --domain "Area One"
```

---

## 6. Creating a doc with full metadata in one call

```bash
ldoc new \
  --type decision \
  --label "Short Noun Phrase" \
  --title "Sentence-length fuller name of the concept" \   # optional; defaults to label
  --summary "1–3 sentence gist that mirrors the doc's opening line." \
  --status living \
  --intent requested \
  --intent-basis "<the person's words, or session/review/clipping + date>" \
  --force should \
  --realization planned \
  --realization-refs <path-or-symbol> \    # optional anchors
  --belongs-to <signpost-ref> \
  --requires <dep-ref> \
  --relates <sibling-ref> \
  --provenance <raw-or-source-ref> \
  --tags-scope <zone> \
  --tags-domain "Area One,Area Two" \
  --body "The doc body. Use - to read from stdin." \
  --dry-run            # preview without writing; drop it to commit
```

`--label` is **required** — a 2–5 word Title-Case noun phrase naming the subject. `--title` is optional and defaults to the label. The facet flags follow the type's row in `doc-types.md`; `ldoc new` refuses a doc that breaks it. Leave out `--intent` only when you mean `incidental` (the default); `--intent requested|chosen` needs `--intent-basis`. Edge refs accept id | label | title and are validated before anything is written. Membership points UP: the child declares `--belongs-to <parent>`, never the reverse.

---

## 7. Don't substitute raw ldoc for the skills

`ldoc` mutators carry no judgment. For substantive work, run the skill that owns
the procedure — it handles concept extraction, blast-radius, cascade, history,
and the post-hoc review summary:

| You want to… | Run |
|---|---|
| Land a request / design / plan into the KB | **apply-to-docs** |
| Bring in external material (notes, RFC, URL, research) | **ingest-reference** |
| Edit / correct / amend an existing doc | **revise-doc** |
| Record decisions already built in a working session | **reconcile-changes** |
| Check whether docs' claims are built; refresh `realization` from the code | **sync-realization** |
| Know what else went stale after a change | **cascade-check** |
| Tidy navigation, orphans, grouping, tree structure | **garden** (or `/garden find homes for orphans`) |
| Refresh a signpost orientation guide | **garden** or **garden-summarize** |
| Periodic cleanup, decomposition, drift repair; work the open flags | **garden** |
| Structural integrity report (no fixes) | **validate** |
| Rebuild `.index/` caches | **reindex** |

When the plugin is installed, these are namespaced `/livedocs:<skill>`.

**Delete vs. deprecate — two distinct retirement paths:**

- **Delete** (`ldoc rm <ref>`) when the doc has no content not already captured
  elsewhere: duplicates, empty stubs, structurally redundant variants where the
  merge preserved everything. Nothing is lost. `ldoc rm` blocks when **any inbound
  edge** exists; `--force` strips **all inbound edges** then deletes and reindexes.
- **Deprecate** (`status: deprecated` + `superseded_by`) when the doc recorded a
  genuine decision or belief that was later overturned. The historical record has
  value even though the doc is no longer authoritative.

The default is NOT to deprecate — that's the right choice only when history
matters. When in doubt: if removing the doc loses no information, delete it.

Planned succession is not deprecation: a still-living current doc may carry
`superseded_by` pointing at the `planned` doc that will replace it, and is
deprecated only once the successor is realized.

Deprecation is a protocol, not a flag flip: add a `## Correction` section, set
`--superseded-by`, then `--status deprecated`, then a history entry — or just let
**revise-doc** handle it. After any batch of writes, run `ldoc validate`.
