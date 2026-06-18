---
name: apply-to-docs
description: >
  Run a request or plan against the live_docs knowledge base before acting on
  it: extract key concepts, map them to existing docs, walk the full impact
  graph to identify the blast radius, warn when that radius is large, then
  batch-synthesize a coherent new state for all affected docs in one pass. Use
  whenever a user request or design plan should be durably recorded — the skill
  ensures live_docs converges to the new intent rather than silently drifting
  from it.
---

# apply-to-docs — Land a request or plan into live_docs

The cardinal rule: **identify the full blast radius before writing a single
byte.** Two passes, cleanly separated:

1. **Identify** — read-only survey of every doc the request touches, including
   cascade neighbors. Produces a complete picture of what will change.
2. **Synthesize** — write all changes in one coherent batch, with the full
   picture in view.

This ordering prevents the sequential-patch problem (each write is informed
only by prior writes, not by the full final state) and makes cycle-safe
graph traversal straightforward (BFS with a visited set during the read-only
pass; no partial updates to reason about).

---

## Step 0 — Capture the episode start time

```bash
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

---

## Step 1 — Receive and normalize the input

Accept the user's request or plan in any of these forms:

- **Inline text** — a request, proposal, or design statement pasted directly.
- **File path** — read the file content.
- **Structured plan** — a numbered list of intended changes / behaviors.

Produce a one-paragraph **plain-language restatement** of what the request
intends: what should be true afterward, what behavior or rule is being
established, what is being changed or discarded. Show this to the user before
proceeding (or proceed silently if the request is unambiguous and short).

When a request is entirely about mechanics ("run validate", "reindex"), there
are no concepts to apply — say so and exit. If the request is clearly
exploratory or hypothetical, run through Steps 2–5 only (present the impact
analysis but skip all writes).

---

## Step 1b — Archive the request as a raw clipping

The user's request is the authoritative provenance source for everything this
skill creates. Archive it now, before any concept extraction, so all new docs
can point back to it.

```bash
python3 scripts/ldoc.py ingest-raw \
  --body "<verbatim request text>" \
  --source "user-request" \
  --title "Clipping: <short description of the request>"
```

Note the returned id: call it **RAW_ID**. This goes to `raw/` — outside the
graph — and is the immutable original.

Then create a normalized reference doc summarizing the request's intent:

```bash
python3 scripts/ldoc.py new \
  --type reference \
  --kind plan \
  --status reference \
  --level incidental \
  --title "Reference: <short description>" \
  --source "raw/<RAW_ID>.md" \
  --body "<the one-paragraph restatement from Step 1>"
```

Note the returned id: call it **REQ_ID**. All new docs created in Step 6c
will use `--provenance <REQ_ID>`.

---

## Step 2 — Extract key concepts

From the normalized restatement, identify 3–10 **key concepts** — the
distinct ideas, rules, constraints, decisions, or behaviors that the request
is asserting. Each concept should be expressible as a short noun phrase.

Label each concept with its likely doc type:

| Concept type | Likely `type` |
|---|---|
| A rule or guideline that should govern future work | `principle` |
| A significant choice with a rationale | `decision` |
| An external force limiting options | `constraint` |
| A must-have behavior or property | `requirement` |
| A user story or workflow | `use-case` |
| A system capability or component | `component` |

When the request describes **how the system should behave** (a behavioral
choice among alternatives), prefer `decision` over `principle`. Principles are
universal guidelines; decisions are specific choices with a rationale.

Record this as a working concept list:

```
Concept: "<short noun phrase>"
  Type:    <principle | decision | constraint | requirement | use-case | component>
  Asserts: <one sentence: the claim this concept makes about how things should be>
```

Extract concepts at the level of **durable claims**, not ephemeral
implementation steps. "We will add a field to the schema" is not a durable
concept; "edge metadata must include a weight field" is.

---

## Step 3 — Survey live_docs for each concept (read-only)

For every concept, search for candidate matching docs:

```bash
python3 scripts/ldoc.py find "<concept noun phrase>"
```

If the first search returns no strong candidates, try alternate phrasings:

```bash
python3 scripts/ldoc.py find "<alternate phrasing>"
```

Also list all docs of the likely type to catch anything text search misses:

```bash
python3 scripts/ldoc.py ls --type <type> --json
```

For each candidate, load the full doc:

```bash
python3 scripts/ldoc.py show <candidate-id>
```

Build a **concept map**: for each concept from Step 2, record zero or more
matching existing docs with their relationship to the new concept's claim:

| Relationship | Meaning |
|---|---|
| `compatible` | Existing doc's claim is fully consistent with the new concept. |
| `partial-supersession` | New concept changes part of the existing doc's claim; the rest remains valid. |
| `full-supersession` | New concept renders the entire existing doc's claim obsolete. |
| `conflict-unresolved` | The two claims are incompatible and need human judgment. |

```
Concept: "<short noun phrase>"
  Asserts: "<new claim>"
  Matches:
    <id>  "<existing title>"  — <relationship>
      Reason: <one sentence>
```

---

## Step 4 — Expand the blast radius via graph traversal (read-only)

The concept map from Step 3 identifies direct matches. Now expand it by
walking the dependency graph from every directly-matched doc. **This entire
step is read-only.**

For each doc in the concept map with a non-`compatible` relationship:

```bash
python3 scripts/ldoc.py neighbors <id> --json
```

This returns `{requires, belongs_to, dependents, relates, provenance}`. Walk
only `requires`/`belongs_to` (upstream) and `dependents` (downstream) — the
hard cascade edges. Skip `relates` and `provenance` (soft navigation edges).

For each neighbor not yet in the concept map, load it and assess whether the
new intent affects it:

```bash
python3 scripts/ldoc.py show <neighbor-id>
```

If it is affected, add it to the concept map with its relationship. If not,
record it as `inconsequential`. Use a visited set to avoid re-walking the
same node (cycle safety).

**Verdict rubric for graph neighbors:**

| Verdict | When |
|---|---|
| `inconsequential` | Neighbor's claim is unaffected by the new intent. The norm. |
| `cascade-extend` | Neighbor is downstream of a changed doc; its content is now stale or misleading and needs revision. |
| `cascade-full` | Neighbor's entire claim is rendered obsolete by the changed upstream. |
| `conflict-unresolved` | The neighbor makes a claim incompatible with the new intent in a way needing human judgment. |

**Frozen-doc rule**: docs with `status: deprecated` or `status: reference`
are frozen — never mark them `cascade-extend` or `cascade-full`. Mark them
`conflict-unresolved` if their claim now contradicts the new intent, and
surface to user.

The result is a **complete impact set**: every doc that will need any change,
with its verdict, before a single write occurs.

---

## Step 5 — Pause gate: warn if blast radius is large

Evaluate the complete impact set from Steps 3–4.

**Trigger this pause if ANY of the following are true:**

- `full-supersession` or `cascade-full` count combined ≥ 2, OR
- All non-`compatible`/`inconsequential` verdicts combined ≥ 4, OR
- Any `conflict-unresolved` docs are present.

If triggered, **stop and present to the user before writing anything:**

```
⚠  apply-to-docs: large impact detected

Your request touches N existing docs:
  full-supersession / cascade-full: N  — these docs will be deprecated entirely
  partial-supersession / cascade-extend: N  — these docs will be revised
  conflict-unresolved: N  — these docs conflict and need your input

Affected docs:
  <id>  "<title>"  verdict: full-supersession
  <id>  "<title>"  verdict: partial-supersession
  <id>  "<title>"  verdict: conflict-unresolved
      Conflict: <one sentence describing the incompatibility>

Continue with these changes? (yes / no / resolve conflicts first)
```

Do not proceed until the user confirms. If the user says "resolve conflicts
first", address the `conflict-unresolved` docs via clarifying questions before
continuing. If the user says "no", exit cleanly with no writes.

If thresholds are not met and there are no unresolved conflicts, proceed
directly to Step 6.

---

## Step 6 — Batch-synthesize all changes

You now hold the complete picture: every doc that will change, and why. Write
all changes in a single coherent pass. The goal is a **consistent new state**
across the entire impact set, not a sequence of minimal patches.

**Write order**: deprecations first (creates `superseded_by` targets), then
revisions, then new docs. Within each category, work from upstream to
downstream so each doc is written with its dependencies already settled.

**For each doc, ask: given everything the new intent asserts, what is the
single correct current state of this doc?** Write that state directly. If
prior text would now be misleading, rewrite it for correctness rather than
qualifying it. The target is a coherent snapshot, not an annotated history.

### 6a — Deprecate fully-superseded docs

For each doc with verdict `full-supersession` or `cascade-full`:

1. Draft the replacement doc body: the single correct current claim.
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
3. Add a `## Correction` section to the deprecated doc explaining why it is
   now wrong and which doc supersedes it. A bare status flip is invalid — the
   Correction section is mandatory. Then deprecate:
   ```bash
   python3 scripts/ldoc.py set <old-id> --status deprecated
   python3 scripts/ldoc.py link <old-id> --superseded-by <REPLACEMENT_ID>
   python3 scripts/ldoc.py history <old-id> --add "apply-to-docs: deprecated — superseded by <REPLACEMENT_ID>: <one-line reason>"
   ```

### 6b — Revise partially-affected docs

For each doc with verdict `partial-supersession`, `extend`, or
`cascade-extend`:

1. Load the current body:
   ```bash
   python3 scripts/ldoc.py show <id>
   ```
2. Rewrite the affected portion to reflect the correct current state. If the
   prior text would now be misleading, rewrite it — do not add qualifiers or
   exception clauses that leave contradictory statements coexisting in the doc.
3. Record the history entry:
   ```bash
   python3 scripts/ldoc.py history <id> --add "apply-to-docs: revised — <one sentence: what changed and why>"
   ```

### 6c — Create new docs for unmatched concepts

For each concept from Step 2 with no matching existing doc (or whose only
matches are frozen/deprecated), create a new doc:

```bash
python3 scripts/ldoc.py new \
  --type <type> \
  --title "<precise, single-responsibility title>" \
  --level <incidental|trial|preference|requirement> \
  --status living \
  --body "<the claim>"
```

**Provenance rule**: every new doc must include `--provenance <REQ_ID>` (the
normalized reference created in Step 1b). This records that the doc was
directly asserted by this user request, not derived from an existing doc.
REQ_ID is in the graph (it lives in `docs/`), so `--provenance` is the correct
edge — do not use `--source`.

Apply `--requires` or `--belongs-to` edges only when a genuine existential
dependency exists, not mere topical proximity.

---

## Step 7 — Validate the store

After all writes, confirm structural soundness:

```bash
python3 scripts/ldoc.py validate
```

Address any ERRORs before finishing. Surface WARNINGs to the user for review.

---

## Step 8 — Report

```
apply-to-docs — complete
Request: "<one-line restatement of the intent>"
RAW_ID:  <id>   raw/<id>.md  — verbatim clipping (not in graph)
REQ_ID:  <id>   docs/<id>.md — normalized reference (provenance anchor)

Concepts identified: N
  "<concept>"  type: <type>  →  <action taken>

Docs changed:
  <id>  "<title>"  deprecated  — superseded by <REPLACEMENT_ID>
  <id>  "<title>"  revised     — <one-line: what changed>
  <id>  "<title>"  created     — new doc for concept "<concept>"

Unchanged docs (compatible / inconsequential):
  <id>  "<title>"

Validation: <N docs scanned — clean | N errors, N warnings>
```

---

## Step 9 — Generate the review summary (FINAL step)

```bash
python3 scripts/ldoc.py review new --since "$START"
```

Report the review id to the user:

```
Review summary created: <id>   (reviews/<id>.md)
```

Review is **post-hoc and non-gating** (see `review-is-post-hoc`): this records
the episode for later signoff and never blocks the apply.

---

## Body-content rule (store-wide convention)

Doc bodies describe the decision or mental model — what is true (or intended)
and why. They do NOT narrate implementation state, absence, or history. If
implementation lags the model, express the gap with `status: target` — the
body need not say so. If prior text would now be misleading, rewrite it;
do not qualify it with exception clauses that leave contradictory statements
in the same doc.
