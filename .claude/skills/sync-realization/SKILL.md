---
name: sync-realization
user-invocable: true
description: >
  Keep the store's `realization` facet in step with the implementation, in both
  directions. Walks every realizable doc in scope (goal, use-case, requirement,
  decision, component), checks the code roots for the thing each doc claims,
  and sets `realization`, `realization_refs`, and `realization_verified` from
  what it finds — never from the doc's own prose. Then surveys the code for
  things that were built but never documented and hands them to
  reconcile-changes. Reports drift: planned docs still unbuilt, realized claims
  the code no longer honors, rules the code contradicts. Never alters a claim.
  Drains `unassessed` docs first. Use after a build, after migrating or
  ingesting a store, before trusting the `planned` backlog, or whenever someone
  asks "is this built?", "are the docs in sync with the code?", or "what's
  actually implemented?".
---

# sync-realization — Check what the docs claim against what exists

The cardinal rule: **the implementation decides realization; the doc never
does.** A realizable doc claims a thing — a component exists, a decision is in
effect, a requirement is met, a use-case is supported, a goal is reached.
Whether that thing exists is a fact about the code roots, and this skill
settles it by looking there. What realization, its companions, and the
`## Implementation` section mean is `.claude/skills/_shared/facets.md`
(realization); which types carry it and with which verb is
`.claude/skills/_shared/doc-types.md`. Read both before starting.

This is what lets agents sync coding work with the design docs and the other
way round: an agent deciding whether it must respect a doc reads its
realization tag from a listing, and an agent choosing what to build next reads
the `planned` backlog. Both only work if the values are true of the code today.

**How this differs from reconcile-changes.** reconcile-changes records what a
session built as new claims. sync-realization makes no claims: it verifies the
claims the store already has against what exists, and updates only the facet
that says whether the implementation has caught up. When it finds something
built that no doc claims, it hands that to reconcile-changes rather than
writing the claim itself.

---

## Non-negotiables

1. **Never alter a claim.** The claim is the body (outside `## Implementation`),
   `title`, `type`, `force`, `imposed_by`, `intent`, `intent_basis`, and
   `status` (`facets.md`). This skill writes only
   `realization`, `realization_refs`, `realization_verified`, and the
   `## Implementation` section — the fields `facets.md` lets an agent update on
   any living doc, whatever its intent. A claim the code contradicts is drift
   to report, never a doc to rewrite, because the code being newer does not
   make it what the person wanted.
2. **Decide realization from the implementation only.** The doc's claim tells
   you what to look for; it is never evidence of whether it exists. Its
   history, its `## Implementation` section, its current `realization`, and
   its existing `realization_refs` are leads to check, not findings. Every new
   value cites what you saw in a code root: an anchor, or the searches that
   came up empty.
3. **Read-only pass over every realizable doc in scope, then one batch
   write.** No `ldoc set` until every doc in scope has a verdict and the
   built-but-undocumented survey is done. Interleaving lets one early write
   colour how you read the next doc, and leaves a half-synced store if the
   episode stops.
4. **Realization-only changes carry a `--note` and do not cascade.** The note
   states previous → new and the evidence, because the review is built from
   the session's change log and that is where the person reads why a value
   moved. No neighbor's claim depends on realization (revise-doc, change
   classification), so cascade-check is not run.
5. **Frozen docs are never written.** `deprecated` and `reference` docs are
   skipped (`facets.md`, status).
6. **Set `realization_verified` only on docs you checked**, and never lower a
   doc's realization because its anchors sit in a code root you were not
   given — that is "not settled," not "not built."
7. **Read-only on the code.** This episode records the gap between docs and
   code; closing it is build work for the backlog, not part of a sync.
8. **One episode, one session, one review**
   (`.claude/skills/_shared/session-lifecycle.md`). Nested skills open none;
   reconcile-changes is handed off, not run inside this session.

---

## Inputs

- **Code roots** — one or more paths to the implementation. A store may
  document several repositories, and its docs need not live in any of them
  (`.live_docs.toml` resolves paths anywhere). With none given, the root is
  the git top-level of the current directory.
- **Scope** (optional) — a `--scope` zone, a `--domain`, or an explicit list
  of doc refs. Default: every living realizable doc in the store.
- **Since** (optional) — a date or commit that bounds the
  built-but-undocumented survey to what changed after it, per root.

**Anchor form.** A ref is a path relative to its code root, optionally
`path#symbol` for a symbol within a file, or a URL as is. A ref in the
repository that holds `.live_docs.toml` is written bare — the form the other
skills already write. A ref in any other root is prefixed with that root's
name, `<root>:path`, where the name is the basename of the root's git
top-level; this keeps refs stable across runs and unambiguous once a store
documents more than one repository.

---

## Step 0 — Resolve inputs, then open the session

Fail loud before opening anything, so a bad invocation leaves no empty
session: a code root that does not exist; a `since` that is neither a date nor
a commit resolvable in every root that is a git checkout
(`git -C <root> rev-parse --verify <since>^{commit}`); a scope that matches no
living realizable doc. Each failure names the input and what to pass instead.

```bash
export LDOC_SESSION=$(ldoc session start)
```

---

## Step 1 — Gather the realizable docs in scope

For each realizable type — `goal`, `use-case`, `requirement`, `decision`,
`component`:

```bash
ldoc find --type <type> --status living [--scope <zone>] [--domain <d>] --json
```

(or `ldoc get <ref...>` for an explicit doc set). Keep, per doc: id, title,
intent, force, current `realization`, `realization_refs`,
`realization_verified`, and `superseded_by`. This is the before-snapshot the
self-check in Step 6 compares against.

**Order the work `unassessed` first**, then docs with no `realization` at all
(legacy docs the migration missed — treat them the same way), then the rest.
`unassessed` docs are the ones every listing currently shows as unknown, so
they are the first thing a sync drains.

---

## Step 2 — Pass 1a: check each doc against the implementation (read-only)

For each doc, in order, decide and record a verdict:

```
<id>  <Intent> <type>: <title>   [force]
  realization: <previous> → <new>      (or "not settled: <why>")
  refs:        <complete anchor list>
  verified:    <stamp>
  evidence:    <one line: what you saw, or what you searched for and did not find>
  implementation section: none | write | refresh | remove
  finding:     none | backlog | regression | contradicts-claim | successor-realized
```

- **Verified stamp.** The commit of the root holding the doc's anchors
  (`git -C <root> rev-parse --short HEAD`) when they all sit in one git
  checkout with no uncommitted changes to the anchored files; otherwise
  today's date (ISO 8601). A commit pins exactly what was checked; a date is
  the honest stamp when no single commit describes it.
- **Refs.** The complete list of anchors where the thing lives now (`ldoc set`
  replaces the list). Drop anchors that no longer resolve; add the ones you
  found.
- **`deferred`.** Check it like any other. If it got built anyway, it moves to
  `realized`; if not, it stays `deferred` and is never a finding.
- **Findings.** `backlog` — a living doc that is `planned` (newly or still).
  `regression` — a doc that was `realized` and the code no longer has the
  thing. `contradicts-claim` — the code does something the claim rules out
  (see Your judgment). `successor-realized` — a living doc whose
  `superseded_by` successor is now realized, so the protocol's deprecation of
  the current doc is due; that is a claim change for revise-doc, not for this
  skill.

---

## Step 3 — Pass 1b: survey for built things with no doc (read-only)

Walk the change surface of each root: with `since`, what changed after it
(`git -C <root> log --name-only <since>..HEAD`, or
`git -C <root> log --name-only --since=<date>`); without
it, the root's top-level structure and entry points. For each durable thing
you find, ask whether a doc in the store already claims it
(`ldoc find <terms> --json`). If one does, it belongs in that doc's refs
(go back and amend its Step 2 verdict). If none does, record it for the
reconcile-changes hand-off with its anchors and one line on why it looks
durable.

---

## Step 4 — Pass 2: write the batch

Only now, write every verdict whose fields changed or whose doc you checked:

```bash
ldoc set <id> --realization <new> --realization-refs <a>,<b> \
  --realization-verified <stamp> \
  --note "realization <previous> → <new>: <evidence>"
```

A re-verified doc with an unchanged value still gets its refs and stamp, with
a note saying it was re-verified — the stamp is what tells the next reader how
fresh the value is. A doc whose verdict is "not settled" is not written.

Where a pointer list is not enough (see Your judgment), write the
`## Implementation` section: take the body from `ldoc show <id>`, replace or
append only that section, and write it back with
`ldoc set <id> --body - --note "<what the section now describes>"`. Every
byte of the body outside that section stays as it was.

---

## Step 5 — Validate

```bash
ldoc validate
```

Address ERRORs this episode caused before closing. Surface WARNINGs. No
reindex.

---

## Step 6 — Report and close (final step)

**Self-check before close:**

- **Claim untouched.** `ldoc get` each written doc and compare against the
  Step 1 snapshot; for a doc whose body you wrote, compare `ldoc show`
  against the body you read in Step 4. Only realization, its companions, and
  the `## Implementation` section differ.
- **Evidence source.** Every note cites a code anchor or an empty search —
  none cites the doc's body, history, or previous value.
- **Stamps.** No `realization_verified` on a doc whose verdict was "not
  settled"; no `unassessed` written by this episode.
- **Drift shape.** No `deferred` doc among the findings. A run that moved many
  docs to `planned` with few searches recorded is skipping the check, not
  finding a backlog.
- **Hand-off.** Nothing in the reconcile-changes list is already claimed by a
  doc.

Print:

```
sync-realization — complete
Code roots: <name> <path> @ <commit|date> ...   Scope: <scope>   Since: <since|—>

Realization changes:
  <id>  "<title>"  <previous> → <new>   — <evidence>   refs: <anchors>
Re-verified, unchanged: <N>  (<ids>)
Not settled: <id> — <why>

Drift:
  Backlog (planned, living):            <id> "<title>" ...
  Regressions (realized → not):         <id> "<title>" — <what is missing>
  Claims the code contradicts:          <id> <Intent> <type> [force] — <what the code does instead>
  Successor realized, deprecation due:  <id> → <successor id>   (hand to revise-doc)

Built, no doc — hand to reconcile-changes:
  <anchors> — <what it is, why it looks durable>

Validation: <clean | N errors, N warnings>
Self-check: <ok, or what you fixed>
```

```bash
ldoc session close --summary "<one-line recap: N docs synced, M drift findings>"
```

Report the review id. If the hand-off list is non-empty, end by naming it as
the next step: run `/reconcile-changes` with the listed anchors as its
description of what changed.

---

## Your judgment

**Locating the implementation for a doc with no refs.** Read the claim for
what to look for, then search the roots with the doc's own vocabulary — its
label, title terms, the names its neighbors' refs use. A component's or
decision's upstream and downstream docs often have refs that point next door.
Entry points (command tables, routes, configuration, public interfaces) are
where a claimed capability usually shows. Weigh how far to search against
what a wrong value costs: marking a built thing `planned` puts finished work
on the backlog; marking an absent thing `realized` lets agents build on
nothing. Absence from the roots you were given is absence only if the thing
belongs there — if other docs' refs name roots you were not given, the doc may
be realized in one of those. When you cannot tell, "not settled" with the
reason is a better outcome than a guess.

**What counts as `partial`.** Ask what a reader acting on the tag would get
wrong. If the core of the claim holds and a stated part is missing, it is
`partial`; if only scaffolding exists — a stub, an unused interface, a flag
nothing enables — `planned` is usually more honest. A goal is reached when the
outcome is observable, not when its components exist; a use-case is supported
when the workflow can be carried out end to end. Another doc's realization
counts as evidence only if you verified it in this episode.

**When the code contradicts the claim.** Report it with the doc's intent and
force, and set realization from what exists (the claim is not in effect, or
only partly). Report the doc's intent and force with the finding: they say
how much stood behind the claim the code departs from. Against an
`incidental` doc the code may well be right; say so, and name revise-doc as
the route if the doc should change. In every case this skill leaves the
claim as it is.

**Whether a pointer list is enough.** Refs answer "where." Write an
`## Implementation` section only when "how" is something a reader cannot
recover from the anchors in reasonable time — the claim is spread across
several roots, or realized by a mechanism whose shape is not visible from any
one file. Refresh an existing section you found stale; remove one that no
longer describes anything.

**What to hand to reconcile-changes.** Something is worth a doc when a later
reader would need to know it exists or why it is shaped that way, and could
not re-derive that from the code: a module boundary, a contract, a
user-facing capability, an architectural choice visible in the code. Internal
helpers, refactors, and implementation detail behind an existing doc are not
— attach them as refs to that doc instead.

---

## Latitude

You decide how far to search, how to read `partial`, and where the line sits
between a built thing worth a doc and detail behind an existing one. If the
scope is too large to check every doc honestly in one episode, narrow it and
say so — draining `unassessed` first — rather than skimming. Surface what the
skill does not cover: a doc that looks mis-typed for its realization (a
"component" that is really a principle), refs that point into a root nobody
named, or a backlog so large it suggests the docs and the code have diverged
in direction rather than in progress.

---

## Checklist before finishing

- [ ] Inputs resolved, failures loud, session opened after resolution.
- [ ] Every living realizable doc in scope has a verdict; `unassessed` and
      realization-less docs drained first.
- [ ] No write before every verdict and the built-but-undocumented survey were
      in hand.
- [ ] Only realization, its companions, and `## Implementation` written; each
      write carries a previous → new note with evidence; no cascade run.
- [ ] `realization_verified` only on checked docs; anchors in the agreed form.
- [ ] Drift reported, `deferred` excluded; contradicted claims reported, not
      rewritten; hand-off to reconcile-changes listed, not run.
- [ ] Validate clean of errors this episode caused; one review, owned here.
