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

This phase **must run inline** in the orchestrator's context — it needs the
entire plan in view to write a coherent batch, so it is never forked.

---

## Nested-invocation rule (read first)

This skill is **always a nested invocation** — the calling orchestrator owns the
episode. It therefore:

- does NOT capture a `START` time or emit any review summary,
- does NOT run `validate` as a gate or re-invoke the orchestrator (the
  orchestrator validates and reports after synthesis),
- does NOT re-walk the graph (that was `assess-blast-radius`) — it acts on the
  plan it was handed.

It leaves a labeled list of writes performed in context for the orchestrator's
report.

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

## Inputs (supplied by the orchestrator)

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
2. Create the replacement:
   ```bash
   python3 scripts/ldoc.py new \
     --type <type> \
     --title "<precise, single-responsibility title>" \
     --level <level> \
     --status living \
     --body "<new claim>"
   ```
   Note the new id: **REPLACEMENT_ID**.
3. Deprecation is a two-part mandatory operation — a bare status flip is invalid.
   Add a `## Correction` section to the deprecated doc's body explaining why it
   is now wrong and which doc supersedes it, then:
   ```bash
   python3 scripts/ldoc.py set <old-id> --status deprecated
   python3 scripts/ldoc.py link <old-id> --superseded-by <REPLACEMENT_ID>
   python3 scripts/ldoc.py history <old-id> --add "synthesize-doc-changes: deprecated — superseded by <REPLACEMENT_ID>: <one-line reason>"
   ```

---

## Step 2 — Revise partially-affected docs

For each doc with verdict `partial-supersession`, `cascade-extend`, or a planned
`revise` action:

1. Load the current body:
   ```bash
   python3 scripts/ldoc.py show <id>
   ```
2. Rewrite the affected portion to its correct current state. If the prior text
   would now be misleading, rewrite it — do not add qualifiers or exception
   clauses that leave contradictory statements coexisting.
3. Record the history entry:
   ```bash
   python3 scripts/ldoc.py history <id> --add "synthesize-doc-changes: revised — <one sentence: what changed and why>"
   ```

---

## Step 3 — Create new docs for unmatched concepts

For each concept with no existing match (or whose only matches are frozen/
deprecated), create a new doc:

```bash
python3 scripts/ldoc.py new \
  --type <type> \
  --title "<precise, single-responsibility title>" \
  --level <incidental|trial|preference|requirement> \
  --status <living|target> \
  --provenance "<anchor id>" \
  --body "<the claim>"
```

**Provenance rule**: every new doc must include `--provenance <anchor>` (the
`REQ_ID`/`NORM_ID` the orchestrator supplied). The anchor lives in `docs/`, so
`--provenance` is the correct edge — do not use `--source` for a graph node.

Apply `--requires` (genuine existential dependency) or `--belongs-to`
(structural parent/child membership) only when that relationship truly exists,
not for mere topical proximity.

**Dedup shortcut**: if a concept merely DUPLICATES or STRENGTHENS an existing
living doc, do NOT create a new doc — instead link the anchor to that doc's
provenance:
```bash
python3 scripts/ldoc.py link <existing-id> --provenance <anchor id>
```

---

## Body-content rule (store-wide convention)

Doc bodies describe the decision or mental model — what is true (or intended)
and why. They do NOT narrate implementation state, absence, or history. If
implementation lags the model, express the gap with `status: target` — the body
need not say so. Strip "extension"/addendum notes that are really migration
plans; if a doc's own claim is wrong, deprecate it with a `## Correction`
section (Step 1) rather than qualifying it.

---

## Output — writes performed

Leave a labeled list in context for the orchestrator's report:

```
Synthesized writes
  <id>  "<title>"  deprecated  — superseded by <REPLACEMENT_ID>
  <id>  "<title>"  revised     — <one-line: what changed>
  <id>  "<title>"  created     — new doc for concept "<concept>"  (provenance <anchor>)
  <id>  "<title>"  provenance-linked — added <anchor>
```

Do not validate or emit a review summary — the orchestrator does both after
synthesis.
