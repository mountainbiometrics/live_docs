---
name: synthesize-doc-changes
user-invocable: false
description: >
  Given a complete plan — the impact set and/or conflict map plus the concept
  list — batch-synthesize the coherent new state for every affected doc and
  write it via ldoc. Deprecate fully-superseded docs (Correction section +
  superseded_by), revise partially-affected docs, and create new docs for
  unmatched concepts, in upstream→downstream order, in one pass. Supplies the
  judgment; ldoc stays the dumb mutator. A phase sub-skill, not meant to be run
  directly by a user.
---

# synthesize-doc-changes — Batch-write the coherent new state (shared phase)

This skill owns the **write pass**: given everything earlier phases discovered
(the concept list from `identify-key-concepts`, the relationship map from
`map-concepts-to-docs`, and where present the impact set from
`assess-blast-radius`), it writes all docs to their single correct current
state in one coherent batch. It supplies the *judgment* (what each doc's correct
state is); the deterministic I/O stays in `ldoc` verbs.

This phase runs inline — it needs the entire plan in view to write a coherent
batch. It writes docs but does no episode bookkeeping: no `START`, no review
summary, no `validate` gate (the caller validates after), and it does not re-walk
the graph (that was `assess-blast-radius`) — it acts on the plan it was handed.
It says nothing about what happens next; whoever invoked it resumes once the
writes are done.

---

## Summary field convention (every doc you write)

When you set a doc's `summary`, keep it **tight: 1–3 sentences, ≤ ~50 words**. It
is the gist a reader needs to decide whether to open the doc — write it like the
doc's opening statement (its Decision/Statement/Context), NOT a recap of the whole
body. Do not pack everything into one run-on sentence (that is not "fewer
sentences"). When the doc's opening is already tight, the summary can be that
opening, lightly condensed. The summary is surfaced verbatim in review snapshots,
search results, and index maps, so it must stay scannable. `ldoc validate` warns
when a summary exceeds ~60 words.

---

## Inputs

- **The plan** — the impact set / conflict map (each affected doc with a verdict
  or planned action) plus the concept list (for new-doc creation).
- **The provenance anchor** — the id new docs should carry (`REQ_ID` for
  apply-to-docs, `NORM_ID` for ingest-reference). Every new doc gets a
  `--provenance <anchor>` edge.

---

## Cardinal rule — coherent state, not minimal patches

You hold the complete picture. For each doc, ask: **given everything the new
intent asserts, what is the single correct current state of this doc?** Write
that state directly. If prior text would now be misleading, rewrite it for
correctness rather than qualifying it — do not leave contradictory statements
coexisting. The target is a coherent snapshot, not an annotated history.

**Write order**: deprecations first (so they create `superseded_by` targets),
then revisions, then new docs. Within each category, work upstream → downstream
so each doc is written with its dependencies already settled.

---

## Step 1 — Deprecate fully-superseded docs

For each doc with verdict `full-supersession` or `cascade-full`:

1. Draft the replacement doc body — the single correct current claim.
2. Create the replacement. Read and apply `.claude/skills/_shared/label-title-summary.md` — `--label` is required and must name the subject (not a fragment); `--title` is optional.
   ```bash
   ldoc new \
     --type <type> \
     --label "<2–5 word Title-Case handle>" \
     --title "<precise, single-responsibility title>" \   # optional; omit if label suffices
     --level <level> \
     --status living \
     --body "<new claim>"
   ```
   Note the new id: **REPLACEMENT_ID**.
3. Deprecation is a two-part mandatory operation — a bare status flip is invalid.
   Add a `## Correction` section to the deprecated doc's body explaining why it
   is now wrong and which doc supersedes it, then:
   ```bash
   ldoc set <old-id> --status deprecated --note "synthesize-doc-changes: deprecated — superseded by <REPLACEMENT_ID>: <one-line reason>"
   ldoc link <old-id> --superseded-by <REPLACEMENT_ID>
   ```

---

## Step 2 — Revise partially-affected docs

For each doc with verdict `partial-supersession`, `cascade-extend`, or a planned
`revise` action:

1. Load the current body:
   ```bash
   ldoc show <id>
   ```
2. Rewrite the affected portion to its correct current state. If the prior text
   would now be misleading, rewrite it — do not add qualifiers or exception
   clauses that leave contradictory statements coexisting. Pass the author note
   inline on the write so it is atomic with the revision:
   ```bash
   ldoc set <id> --body - --note "synthesize-doc-changes: revised — <one sentence: what changed and why>"
   ```

---

## Step 3 — Create new docs for unmatched concepts

For each concept with no existing match (or whose only matches are frozen/
deprecated), create a new doc. Read and apply `.claude/skills/_shared/label-title-summary.md` — `--label` is required and must name the subject (not a fragment); `--title` is optional.

```bash
ldoc new \
  --type <type> \
  --label "<2–5 word Title-Case handle>" \
  --title "<precise, single-responsibility title>" \   # optional; omit if label suffices
  --level <incidental|trial|preference|requirement> \
  --status <living|target> \
  --provenance "<anchor id>" \
  --belongs-to <nearest-signpost-id> \
  --body "<the claim>"
```

Use `--belongs-to` per the shared placement policy whenever a visible coherent
signpost exists in the concepts/edges already in hand. Omit only when no good
parent is visible (defer to gardening rather than force a bad home).

**Domain origination** — the parallel axis to `belongs_to` placement. **Read and
apply** `.claude/skills/_shared/domain-tagging.md`; your role here is the
**originator**. At doc creation, originate applicable `domain` tags via
`--tags-domain "..."`. Because you are tagging in isolated context, **tag
liberally** — apply every domain that plausibly applies (optimize for recall);
do NOT guess conservatively, since gardening (with full-store context) is what
prunes. Two rules from the shared policy: **consult `ldoc domains` and reuse an
existing domain over coining a new synonym**; and a term that is really a domain
goes in `--tags-domain`. Ingest originates liberally; gardening prunes
authoritatively.

**Provenance rule**: every new doc must include `--provenance <anchor>` (the
`REQ_ID`/`NORM_ID` the orchestrator supplied). The anchor lives in `docs/`, so
`--provenance` is the correct edge — do not use `--source` for a graph node.

### Wiring `belongs_to` and `requires` (do not conflate them)

**Read first:** `.claude/skills/_shared/belongs-to-placement.md` — apply verbatim
when choosing a parent. Ingest **originates** placement at birth; gardening
refines later.

These are two different axes:

- **`belongs_to` = the hierarchy / membership DAG.** It is the *acyclic* structural
  axis: a doc declares membership in the parent that defines its grouping, and
  **removing the parent would orphan it**. Test: *"If the parent concept didn't
  exist, would this doc be homeless / meaningless as a standalone entry?"* If yes,
  it `belongs_to` that parent.
- **`requires` = the logical-dependency web.** It may cycle; it is reverse-cascading
  ("if the required doc changes, re-evaluate this one"). It is NOT structural and
  does NOT place a doc in the navigation hierarchy.

**Nest clear clusters — this is not "being non-conservative."** When the concepts
you are creating form a coherent cluster *and one of them states the over-arching
concept that the others elaborate* (the decisions/constraints that define how that
concept works), the elaborating docs **`belongs_to` the defining doc**, which in
turn `belongs_to` whatever broader grouping it sits in. Wiring those members
straight to the broad top-level signpost instead — flattening the cluster — is not
caution; it misreads `belongs_to`, because each member *would* be orphaned without
the concept it elaborates. The defining doc thereby becomes a descendant-bearing
signpost (signposts are structural, not a type — see garden-hierarchy).

What conservatism actually forbids is `belongs_to` for **mere topical proximity**:
two docs that merely share a subject, where neither would be orphaned by the
other's removal, get `relates` (or just a shared `domain`/`scope` tag), never
`belongs_to`. A member often *both* `belongs_to` its defining concept (membership)
and `requires` it (existential dependency) — wire both when both hold, but never
substitute one axis for the other.

**Level classification — claim authority, not "has a provenance edge".**
`level` is the settledness/authority of the *claim*. Every new doc in this
pass already gets `--provenance <anchor>`, so "has a provenance edge" must
**not** be treated as grounds for `trial` / `preference` / `requirement` —
that reading makes `incidental` unreachable and is the observed failure mode.

- Default new claims to **`level: incidental`** when the provenance anchor does
  not contain an explicit user utterance (or clear confirmation) of *this*
  claim. Agent-articulated generalizations, mechanisms the user only saw in a
  report, and "the user didn't contradict it" are incidental — silence is not
  ratification.
- Raise to `trial` / `preference` / `requirement` only when the source evidence
  for *this claim* supports that settledness. Do not inflate because the claim
  feels important, because `type: requirement` is nearby in the taxonomy, or
  because the episode archived a request/digest.
- `level: requirement` means high settledness of the claim, **not** "this doc's
  type is requirement" and **not** "future agents must treat this as user law."

**Vocabulary for labels/titles.** Prefer the source material's own words (user
utterances, established project terms, lexicon hits). An agent-coined name that
does not appear in the source is a proposal — do not canonize it as the durable
handle when the source already named the thing differently. If the user rejected
a term and supplied another, use theirs. (Apply `_shared/label-title-summary.md`
as usual; this is an additional naming constraint.)

**Attribution honesty.** Never write that the user stated or ratified a claim
unless the provenance anchor contains that utterance (or an explicit
confirmation). State the claim without false speaker attribution. Consumer
stores may keep their own body conventions for attribution; when you follow
one, evidence still binds — do not blanket-stamp a batch with identical
attribution that the source does not support.

**Thin decisions wire to roots.** When this batch creates both a why-root and a
decision/component that instantiates it, the thin doc **`requires`** the root
(and often `belongs_to` it when membership holds). Do not leave the root only
as prose inside the decision body.

**Dedup shortcut**: if a concept merely DUPLICATES or STRENGTHENS an existing
living doc, do NOT create a new doc — instead link the anchor to that doc's
provenance:
```bash
ldoc link <existing-id> --provenance <anchor id>
```

---

## Body-content rule (store-wide convention)

Doc bodies describe the decision or mental model — what is true (or intended)
and why. They do NOT narrate implementation state, absence, or history. If
implementation lags the model, express the gap with `status: target` — the body
need not say so. Strip "extension"/addendum notes that are really migration
plans; if a doc's own claim is wrong, deprecate it with a `## Correction`
section (Step 1) rather than qualifying it.

Apply `_shared/doc-style.md` for writing discipline. Apply
`_shared/cruft-verdicts.md`'s detection lens here too, including its
incidental-detail-vs-the-decision's-subject test, not only during gardening.

---

## Output — writes performed

Emit a labeled list of the writes performed:

```
Synthesized writes
  <id>  "<title>"  deprecated  — superseded by <REPLACEMENT_ID>
  <id>  "<title>"  revised     — <one-line: what changed>
  <id>  "<title>"  created     — new doc for concept "<concept>"  (provenance <anchor>)
  <id>  "<title>"  provenance-linked — added <anchor>
```
