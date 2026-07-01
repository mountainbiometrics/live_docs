---
name: map-concepts-to-docs
user-invocable: false
description: >
  Given an extracted concept list, query the live_docs KB and map
  each concept to existing docs, recording the relationship: compatible,
  partial-supersession, full-supersession, or conflict-unresolved. Owns the
  shared survey + dedup-and-conflict scan that apply-to-docs, ingest-reference,
  and revise-doc each used to inline. Read-only — produces a relationship
  verdict map, writes nothing. A phase sub-skill, not meant to be run directly
  by a user.
---

# map-concepts-to-docs — Map concepts to existing docs (shared phase)

This skill owns the **one** read-only survey that turns a concept list into a
relationship verdict map. It is invoked after `identify-key-concepts` by the
governed-write orchestrators. **This entire skill is read-only** — it issues only
`ldoc find`/`ls`/`show`/`neighbors`, writes nothing, and does no episode
bookkeeping (no `START`, no review). It says nothing about what happens next —
whoever invoked it resumes their own work once the verdict map exists.

---

## Inputs

- **The concept list** from `identify-key-concepts` (each with its
  `Type` and `Asserts` sentence).
- **The scan emphasis** — a knob the caller passes:
  - apply-to-docs / ingest-reference: full concept survey across the store.
  - revise-doc: a dedup/conflict scan focused on the target doc's neighbors and
    same-type docs (does the revision duplicate or contradict an existing
    claim?).

---

## Step 1 — Survey candidate docs for each concept

For every concept, search for candidate matching docs using its `Asserts`
sentence as the search key:

```bash
ldoc find "<concept noun phrase or key claim>"
```

If the first search returns no strong candidates, try alternate phrasings:

```bash
ldoc find "<alternate phrasing>"
```

Also list all docs of the concept's likely type to catch anything text search
misses:

```bash
ldoc ls --type <type> --json
```

**`ldoc find` alone is insufficient — add cluster-scoped reasoning.** Lexical
search queries the store with the NEW claim's vocabulary, so a stale doc whose
text predates the new terminology is *never retrieved* — the systematic miss.
This is the core detection gap, so for every concept that touches a subsystem,
ALSO pull all living docs in that `belongs_to` cluster / `scope` zone and
**reason** over them rather than trusting lexical overlap:

```bash
ldoc find --scope <zone>              # everything anchored in the scope zone
ldoc graph <signpost> --direction down   # the cluster under the relevant signpost
ldoc ls                               # / neighbors, to walk the cluster
```

Then, for each living doc in the cluster, ask: **"does the new architecture make
this obsolete?"** — a reasoning judgment, not a keyword match. A doc the new
intent supersedes will routinely share zero query terms with it; cluster-scoped
reasoning is how those are caught.

For a dedup/conflict scan around an existing target doc (revise-doc's emphasis),
also pull the doc's neighbors so upstream and downstream candidates are included:

```bash
ldoc neighbors <target-id> --json
```

For each candidate, load the full doc and read it:

```bash
ldoc show <candidate-id>
```

To surface dangling edges across the store before relying on the graph, run
`ldoc edges --json` and check the `dangling` key; surface any
to the user.

---

## Step 2 — Classify the relationship for each match

For each concept, record zero or more matching existing docs with the
relationship of the concept's claim to that doc's claim:

| Relationship | Meaning |
|---|---|
| `compatible` | Existing doc **already asserts** the new concept's claim — no write needed. |
| `partial-supersession` | Existing doc asserts a thinner, partial, narrower, or staler version of the claim (or changes only part of it); REVISE it to carry the fuller claim. |
| `full-supersession` | New concept renders the entire existing doc's claim obsolete. |
| `conflict-unresolved` | The two claims are incompatible and need human judgment. |

The source rarely says "doc 1234 is wrong" outright — it just asserts a concept
that contradicts an existing claim. Judge the substance, not the wording.

**`compatible` requires the doc to already make the same claim — not merely the
same subject.** Being about the same topic, or being adjacent, is not
`compatible`. Before writing `compatible`, apply this test: **does this doc, as
written, already state the concept's `Asserts` sentence?** If it only states a
weaker, partial, or narrower version — e.g. it covers the mechanical rule but not
the conceptual claim behind it — that is `partial-supersession` (→ REVISE), not
`compatible`. Cleaning up the doc to carry the updated claim is the entire point
of the system; a `compatible` verdict that leaves a thinner doc in place is
silent drift.

**Bias rule**: reserve `compatible` for genuine full matches where the claim is
already present; when the existing doc is only topically related, weak, or
partial, prefer `partial-supersession` over `compatible`, and prefer surfacing a
`conflict-unresolved` over silently accepting a weak match — silent drift is
worse than a flagged conflict or a surfaced revision.

**Sibling / back-reference scan.** When a concept is classified
`full-supersession` against doc X, the OLDER victim the new concept contradicts
is usually X's `belongs_to` sibling — a replacement and the thing it replaces
typically share a parent signpost. So scan X's siblings (same parent) and
classify the new concept against them too:

```bash
ldoc neighbors <X-id> --json     # read X's belongs_to parent, then its children
```

Don't stop at the first match; the more important supersession target is often
the sibling, not X itself.

**Document-level re-ingestion dedup.** Track, across the whole concept list, how
each source's concepts map. When a HIGH FRACTION of a single source's concepts
all map to one prior normalized/NORM reference doc, the source is a
**re-ingestion of already-ingested material** — not new knowledge. Flag this in
the output so the caller updates the existing docs instead of silently creating a
duplicate NORM. map-concepts owns the *detection* and surfaces the flag; the
*reaction* (update-existing vs create-new) lives in ingest-reference.

---

## Output — the relationship verdict map

Emit a labeled verdict map:

```
Concept: "<short noun phrase>"
  Asserts: "<new claim>"
  Matches:
    <id>  "<existing title>"  — <compatible | partial-supersession | full-supersession | conflict-unresolved>
      Reason: <one sentence>
  Action planned: <revise | deprecate | link-provenance | create-new>
```

Concepts with no match (or whose only matches are frozen/deprecated) are
candidates for new docs. **Correcting stale existing docs is the highest-value
output** — existing docs have dependents that cascade-check will propagate to;
freshly created docs have none.

When the re-ingestion dedup above fires, surface it alongside the map:

```
Re-ingestion flag: <N of M> concepts from this source map to <NORM-id>
  → likely re-ingestion; caller should update existing docs, not create a duplicate NORM.
```

### Verdict-map sanity check — zero supersessions is a red flag

Before emitting, look at the whole map. **If the input is a system-changing
initiative yet the map produced NO `full-supersession` / `partial-supersession`
verdicts, treat that as a likely MISS, not a conservative win.** "The new intent
changes how X is built, yet no X-doc changed" is suspicious — almost always a
lexical miss where the stale doc's vocabulary predates the new claim. Do not ship
the all-`compatible` map: re-run the cluster-scoped reasoning above over the
affected `scope` zones and re-examine each living doc by reasoning before
concluding nothing was superseded.
