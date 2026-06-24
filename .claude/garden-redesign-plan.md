# Gardening redesign — decomposition plan

Status: **implemented** (skills + ldoc keywords; decision docs were already in KB).

Goal: decompose the monolithic `garden` skill into a *thin dispatcher* over a
family of independently-runnable, individually-tunable gardening sub-skills —
mirroring the ingest pipeline's composition pattern
([Decision 20260618214203](../kb/02-docs/20260618214203.md): shared phases →
named sub-skills; orchestrators are thin compositions). Reconcile
`curate-grouping` and `summarize-descendants` into that same family.

---

## 1. The three axes (why this decomposition)

Gardening currently conflates three independent concerns. Splitting along them is
what makes each separately tunable:

- **Atomicity** — the *size/ownership* of a doc. One responsibility = one owner.
  Two opposite moves: split overloaded docs, and merge/fold duplicate-or-cruft docs.
- **Structure** — *where* a doc lives. Homes for orphans, right-sized branches,
  scope anchors, refreshed signpost guides.
- **Form** — *surface quality* independent of structure. Naming, summaries,
  body shape, schema normalization, findability (keywords).

---

## 2. The sub-skill family

Every sub-skill is `user-invocable: false` — a pure phase, never run directly.
The only entry point is `/garden` (§3); to tune one aspect you invoke the
dispatcher with natural-language intent (`/garden clean up duplicates`) and it
routes to the right phase. All share the common contract in §4.

### Atomicity

#### `garden-decompose`  *(= today's Pass 1, unchanged in spirit)*
- **Goal:** find docs carrying >1 responsibility and split them.
- **Signals:** multiple unrelated `##` sections; title with "and"/list;
  long `requires`; hot-file (history ≥5 with mixed-topic summaries —
  [Decision 20260615203928](../kb/02-docs/20260615203928.md)).
- **Moves:** create A/B docs; deprecate original with `## Correction` +
  `superseded_by`; rewire inbound edges; reclassify edges. Reports changed ids;
  the dispatcher cascades.

#### `garden-collapse`  *(NEW — the inverse of decompose)*
- **Goal:** enforce *singular ownership*. A claim with three partial "owners" has
  no real owner. Merge duplicates and fold cruft.
- **Signals:**
  - Near-duplicate docs (same claim asserted in ≥2 docs — the dedup notion
    `map-concepts-to-docs` already uses).
  - **Shared-ownership smell:** one responsibility spread thin across several
    docs, none of which fully owns it.
  - **Cruft:** `level: incidental`, no dependents, thin body, not navigationally
    useful on its own — a candidate to fold into its parent/owner *without*
    making the parent less singular.
- **Moves:**
  - *Merge:* pick the survivor; port unique content into it; deprecate the others
    with `superseded_by → survivor` + `## Correction`; rewire inbound edges to
    survivor.
  - *Fold:* merge a trivial child's content into its parent body; deprecate the
    child; rewire edges. Only when it doesn't overload the parent (i.e. doesn't
    re-create a decompose smell).
  - Always: `## Correction` + history entry; report changed ids (the dispatcher
    cascades).
- **Guardrail:** collapse and decompose are antagonists; `garden all` runs
  decompose *before* collapse, and collapse must not fold anything that would trip
  decompose's "two reasons to change" test.

### Structure

#### `garden-hierarchy`  *(= `curate-grouping` reconciled with scope + re-scoping)*
Absorbs three things that are currently split or missing:
- **(a) Grouping / orphan homes** — all of today's `curate-grouping`: survey
  orphans + thematic clusters, decide which coherent themes deserve a signpost,
  create signposts, wire `belongs_to`. (Keep the editorial "fewer, tighter
  groupings" bias and the "a signpost is a curated directory, not an auto-dump"
  rule.)
- **(b) Scope anchors** — today's `garden` Pass 5 Part A: descendant-bearing
  structural docs that should declare a distinct `scope` anchor (or that
  redundantly restate the parent's). Folded in because placing a doc in the tree
  and anchoring that subtree's scope are the same editorial act.
- **(c) Re-scoping overgrown branches** *(NEW — your "100 docs in a branch"
  point)*. A signpost whose direct-child count or subtree size exceeds a
  threshold (start ≈ 12 direct children / configurable) is a smell even though
  every child is *properly* in the tree. If the children cluster into sub-themes,
  propose intermediate signposts and re-home the children one level down. This is
  the structural analogue of decompose: "in the tree" is necessary but not
  sufficient; the tree must stay navigable.
- **Finisher:** invoke `garden-summarize` (nested) on every signpost whose
  membership changed.
- **Replaces:** standalone `curate-grouping` (deprecate that skill, or make it a
  thin alias that forwards here).

#### `garden-summarize`  *(= `summarize-descendants`, renamed into the family)*
- Unchanged behavior: (re)write a signpost's body as an orientation guide +
  tight frontmatter `summary`. Synthesize, don't concatenate.
- **Still invocable by other orchestrators** — `cascade-check`
  (descendant-summary verdict) and `garden-hierarchy` call it via the Skill tool.
  `user-invocable: false` hides it from the user's slash list but does not stop an
  orchestrator from invoking it. It never owns an episode; the caller does.
- Old name kept as an alias so cascade-check's existing references keep resolving.

#### `garden-domains`  *(= today's Pass 5 Part B)*
- The cross-cutting `domain` curation: the ≥2-scopes test, align untagged docs,
  retire/split stale or over-broad domains. Kept separate from `garden-hierarchy`
  because `domain` is orthogonal to topology (a flat applied tag, not inherited).

### Form

#### `garden-refine`  *(NEW — your "refinement" pass; also subsumes field-aliases)*
- **Goal:** catch the intermittent surface-quality drift left by agentic
  ingestion (subagents formatting inconsistently). **Sampling-based**, since the
  inconsistency is sporadic: spot-check a random or triage-flagged sample.
- **Checks / moves:**
  - **Truncated / lazy labels & titles** — your "ddl entities are", "State Policy
    is" examples. These are *semantic* truncations `validate` can't catch
    (validate only checks trim + uniqueness). LLM judgment: is this a real,
    complete noun-phrase title? If not, rewrite via `ldoc set --title/--label`.
  - **Summary presence & quality** — every doc has a real signpost summary
    sentence, not a fragment or a copy of the body's first line.
  - **Body-shape consistency** — flag docs that are a bare paragraph where the
    type conventionally has structure (e.g. a `decision` with no
    context/decision/consequences shape) and vice-versa. Normalize *lightly* —
    don't impose rigid templates; just fix the clearly-lazy ones.
  - **Schema normalization** *(replaces Pass 4 field-aliases — no JSON file)* —
    fold any legacy fields/enum values to canonical per the schema doc
    + `ldoc validate` output. Driven by the canonical schema, not a checked-in
    alias map.
  - **Keywords curation** — populate/curate the new `keywords` frontmatter list
    (see §3) so `ldoc find` surfaces the doc under the terms a searcher would use.
- All writes non-destructive (history entry each); never changes meaning.

#### `garden-integrity`  *(= today's Pass 3 `consistency`)*
- Mechanical structural repair: broken `requires`/`belongs_to` refs, missing
  required fields, `id != filename`, deprecated-without-`superseded_by`. Wraps
  `ldoc validate` and **applies** fixes (vs `validate` which only reports).
- Kept distinct from `garden-refine`: integrity is mechanical/objective, refine is
  editorial/subjective.

### Dropped

- **Pass 2 `staleness`** as a standalone pass — it never writes, and
  `cascade-check` already owns "a dependency changed after its dependent." Its
  read-only kernel moves into the dispatcher's triage scan (§3) as a routing
  signal, not a skill.

---

## 2a. Shared policy: what makes a good `belongs_to` (cross-skill prose include)

A single shared prose fragment — **not a skill** — defining "what a good
`belongs_to` placement looks like." This is the boilerplate-include fallback that
[Decision 20260618214203](../kb/02-docs/20260618214203.md) explicitly reserves for
shared *text* (vs. shared *procedure* → sub-skill). Lives once (e.g.
`.claude/skills/_shared/belongs-to-placement.md`) and is referenced verbatim by:

- **`synthesize-doc-changes`** (ingest's writer) — so a newly created doc gets a
  **semi-adequate starting parent at birth** instead of being dumped as an orphan
  for gardening to clean up. It need not analyze the whole KB — just pick the best
  visible signpost from the concepts/edges already in hand.
- **`garden-hierarchy`** — the authoritative refiner that later second-guesses and
  improves those placements with full-store context.

The policy captures (to be written): prefer the *nearest* coherent signpost over
the root; a placement is a navigational claim, not a tag; one primary parent;
"in the tree somewhere" is necessary but not sufficient (it must be the *right*
branch and a right-sized one); when no good parent is visible, leave it to
gardening rather than forcing a bad one. Single source of truth so ingest and
gardening can't drift apart on the definition.

> **Ingest fix tied in here:** today ingest skips initial `belongs_to` because
> "placement is a gardening concern." The fix is for `synthesize-doc-changes` to
> apply this shared policy at creation time — cheap, local, semi-adequate —
> leaving gardening to *refine* placements, not *originate* all of them.
>
> *Grounding note (from the conflict survey):* the current store has **no orphan
> debt to point at** — `ldoc orphans` returns only `type: reference` clippings,
> which are correctly outside the tree; zero living atomic docs are orphaned. So
> justify this change on its own merits (lower future gardening load, better
> birth placement, ingest/gardening sharing one definition), **not** as "fixing
> existing orphan debt." Don't overstate the symptom.

---

## 3. The `garden` dispatcher (the only entry point)

`/garden` is the sole user-facing command. It **owns the whole episode**: the
single START timestamp, the routing decision, one `cascade-check` over the union
of all changed docs, and the one `ldoc review new`. Sub-skills are pure phases it
invokes via the Skill tool; none captures a START, cascades, or emits a review.

Invocation:

- **`/garden` (no arg) — triage + route.** Cheap read-only scan; fire the phase(s)
  the store most needs; if nothing glares, sample a couple. Triage → routing:
  | Signal (cheap query) | Route |
  |---|---|
  | `ldoc orphans` count high | `garden-hierarchy` |
  | any signpost with subtree/direct-children over threshold | `garden-hierarchy` (re-scope) |
  | `ldoc validate` errors | `garden-integrity` |
  | hot-files (history ≥5, mixed summaries) present | `garden-decompose` |
  | near-duplicate titles/summaries detected | `garden-collapse` |
  | else | random-sample 1–2 of {refine, domains, decompose} |
- **`/garden <natural-language intent>` — map intent to phase(s).** The dispatcher
  reasons from intent to the right sub-skill(s):
  `/garden clean up duplicates` → `garden-collapse`;
  `/garden find homes for the orphans` → `garden-hierarchy`;
  `/garden fix the cut-off titles` → `garden-refine`. It still owns the episode.
- **`/garden all` — full sweep in dependency order:**
  `decompose → collapse → hierarchy → domains → refine → integrity → summarize`.
  (Atomicity before structure so homes reflect final docs; summarize last so
  guides reflect final memberships.)

**Episode close (any mode that wrote anything):** one `cascade-check` from the
union of changed ids → resolve verdicts (incl. re-running `garden-summarize` on
flagged signposts) → one `ldoc review new`. A run that wrote nothing emits no
review.

---

## 4. Common sub-skill contract (every `garden-*` phase)

Modeled on ingest's phase sub-skills (`identify-key-concepts` et al.) — **no
dual-mode**:

- **Always nested, never an episode owner.** `user-invocable: false`. The phase
  does its one job, applies its writes, and **reports the ids it changed**. It
  captures no START, runs no `cascade-check`, emits no review — the dispatcher
  (§3) owns all three.
- **Apply-and-review discipline** (unchanged): applies the judgment it deems
  correct; correctness is caught *post-hoc* by the review summary, not a pre-write
  gate ([review-is-post-hoc 20260616181719](../kb/02-docs/20260616181719.md)).
  Deprecations/merges land with a `## Correction`; every touched doc gets a
  history entry.
- **Output shape:** `garden — phase: <name> / Scanned / Findings / Actions /
  Applied / Changed-ids`. The Changed-ids list is what the dispatcher unions for
  the closing cascade.

---

## 5. The `keywords` field (separate schema workstream)

Does not exist today — `ldoc find` searches title+label+body and filters
`--scope`/`--domain` only. This is an `ldoc` change, recorded as a decision doc.

- **Schema:** add `keywords:` — a flat frontmatter list (like `domain`, NOT
  inherited, NOT a cascade edge). Optional; omitted = empty.
- **`ldoc` changes:**
  - `ldoc new` / `ldoc set` accept `--keywords` (comma-separated, replace
    semantics — same shape as `--domain`).
  - `ldoc find` includes `keywords` in its term match (alongside title/label/body),
    and optionally a `--keyword` filter.
  - `validate`: keywords are free-text, trimmed, de-duped per doc; no resolution
    needed.
- **Ownership:** `garden-refine` curates them. Distinct from `domain` (business
  grouping / ≥2-scopes facet) — keywords are *search synonyms / aliases* for
  findability, no governance bar.
- **Record:** a `decision` doc ("keywords: a findability field distinct from
  domain") via the normal ingest/apply path.

---

## 6. Migration map

| Today | Becomes |
|---|---|
| `garden` Pass 1 single-responsibility | `garden-decompose` |
| `garden` Pass 2 staleness | dropped → dispatcher triage signal |
| `garden` Pass 3 consistency | `garden-integrity` |
| `garden` Pass 4 field-aliases (JSON) | folded into `garden-refine` (no JSON) |
| `garden` Pass 5 Part A scope anchors | folded into `garden-hierarchy` |
| `garden` Pass 5 Part B domains | `garden-domains` |
| `curate-grouping` (standalone) | `garden-hierarchy` (absorbs it; +re-scoping) |
| `summarize-descendants` | `garden-summarize` (alias kept) |
| — | `garden-collapse` (NEW) |
| — | `garden-refine` (NEW) |
| — | shared `belongs-to-placement` prose include (NEW; §2a) |
| `garden` (monolith) | thin dispatcher (owns START, cascade, review) |
| `synthesize-doc-changes` punts on `belongs_to` | sets a starting parent via the shared include |

---

## 7. Build order

1. **`keywords` schema + `ldoc` support** (unblocks `garden-refine`); record the
   decision doc.
2. **Shared `belongs-to-placement` include** (§2a) + wire `synthesize-doc-changes`
   to apply it at doc creation (the ingest fix).
3. **Extract the easy lifts** into `user-invocable: false` phase sub-skills with
   the §4 contract: `garden-decompose`, `garden-integrity`, `garden-domains`
   (mostly moving existing prose), and rename `summarize-descendants` →
   `garden-summarize` (+ alias).
4. **`garden-hierarchy`** — port `curate-grouping`, fold in scope-anchoring + the
   shared placement include, add the re-scoping recursion. Deprecate/alias
   `curate-grouping`.
5. **`garden-collapse`** and **`garden-refine`** — the two genuinely new phases.
6. **Rewrite `garden`** as the dispatcher (§3) that owns START + cascade + review;
   update callers (cascade-check references to `summarize-descendants`).

---

## 8. Open knobs to tune later (not blockers)

- Re-scoping branch-size threshold (start ≈12 direct children).
- Hot-file history threshold (currently 5).
- `garden` no-arg sampling policy (how many passes, weighting).
