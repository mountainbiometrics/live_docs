---
name: curate-grouping
description: >
  Survey the live_docs store and PROPOSE how docs should be grouped under
  navigational index/MOC docs — which coherent themes deserve a `type: index`
  signpost, and which docs should `belongs_to` which index. This is the agentic
  curation decision: it reads orphans, shared domain/scope, requires/relates
  clusters, and thematic coherence, then proposes new index docs and belongs_to
  memberships. Proposal-only — the human confirms before any write, exactly like
  garden. Use when the store has grown enough that navigation needs signposts,
  when orphans accumulate, or when an existing index has become too broad and
  should split. An index is a curated directory page, NOT an auto-dump.
---

# curate-grouping — Decide what belongs under an index/MOC (proposal-only)

The cardinal rule: **an index/MOC is a navigational signpost a human would want
to land on** — a "this grouping contains these things" page, like a curated
directory index. It is NOT an auto-dump of everything that happens to share a
tag. The judgment here is *editorial*: which groupings are coherent enough to
deserve a signpost, and which doc genuinely belongs under each.

This skill **proposes** groupings and (only on user confirmation) **applies**
them — it never silently creates index docs or rewires `belongs_to` edges. The
same proposal-only discipline as `garden`.

It decides the *structure* (which indexes exist, who belongs to whom). It does
NOT write the aggregated overview prose — that is `summarize-descendants`, run
after the memberships are confirmed.

---

## Episode start time

Before beginning, capture the current UTC time (used only if the pass actually
writes — a pure proposal that writes nothing emits no review summary):

```bash
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

---

## Step 1 — Survey the store for grouping signals

Read, do not write. Gather the inputs an editor would use to spot coherent
groupings:

1. **Existing indexes and their current membership** — so you extend rather
   than duplicate. `hierarchy.md` lists each `type: index` doc and the docs that
   hard-edge into it:
   ```bash
   python3 scripts/ldoc.py ls --type index --json
   ```
   and read `kb/02-docs/.index/hierarchy.md` for the current rollup of each
   index's `belongs_to` children.
2. **Orphans** — disconnected docs are the prime candidates for a home. Read
   `kb/02-docs/.index/orphans.txt` (from the last reindex); `index`/`type` docs
   are exempt there by design.
3. **Shared `domain` / `scope`** — docs tagged into the same area are a thematic
   cluster signal:
   ```bash
   python3 scripts/ldoc.py find --domain "<domain>" --json
   python3 scripts/ldoc.py find --scope "<scope>" --json
   ```
4. **`requires` / `relates` clusters** — docs that depend on or see-also each
   other form natural neighborhoods:
   ```bash
   python3 scripts/ldoc.py neighbors <id> --json
   python3 scripts/ldoc.py graph <id> --depth 2 --direction both --json
   ```
5. **Full inventory** for thematic coherence — skim titles/types to recognize a
   theme text search would miss:
   ```bash
   python3 scripts/ldoc.py ls --json
   ```

---

## Step 2 — Judge which groupings deserve an index

A signal cluster is not automatically an index. Apply editorial judgment:

**When an index SHOULD exist:**

- Several living docs share a coherent theme a reader would navigate to as a
  unit ("everything about the cascade engine", "the edge-typing decisions"), AND
- a person landing on a "this grouping contains these things" page would find it
  genuinely useful as a starting point, AND
- the grouping has enough members (≈3+) to be worth a signpost — two docs that
  already `relate` to each other do not need an index.

**When an index should NOT exist (leave the docs as-is):**

- The "theme" is just a shared tag with no narrative throughline — that is what
  `find --domain` is for; do not reify every tag as an index.
- The members are better expressed as a `requires`/`relates` cluster than a
  parent/child hierarchy.
- A single doc would be the only member.

**When an existing index is TOO BIG and should split:**

- Its members span more than one coherent sub-theme — a reader scanning the Map
  would not perceive one subject. Propose splitting into two narrower indexes,
  each a tighter signpost, and reassign each member to the right one.
- Symptom: you would describe the index as "X and also Y."

**When a doc is MISCATEGORIZED:**

- A member's subject does not match the index's theme — propose moving its
  `belongs_to` to a better-fitting index (or removing the membership if none
  fits and the doc stands alone).

**Bias rule:** prefer *fewer, tighter* indexes. An index that tries to hold
everything is navigation noise. Prefer leaving a doc ungrouped over forcing it
under a loosely-related index — a wrong grouping misleads a navigator worse than
no grouping does.

---

## Step 3 — Compose the proposal

For each grouping decision, propose concretely. Two kinds of proposal:

**(a) New `type: index` doc** for a coherent theme that lacks a signpost:

- Suggested title (a navigational name: "Index: <theme>") and `label`.
- One-line statement of what the grouping is — the editorial throughline that
  makes these docs one subject.
- The list of member ids that would `belongs_to` it.
- Its place in the hierarchy: does it `belongs_to` the root index
  (`20260615090011`) or a broader index?

**(b) `belongs_to` membership wiring** for existing docs (including orphans)
into an existing or proposed index:

- Member id → target index id, with a one-clause reason it belongs.

**(c) Split / recategorize** proposals where Step 2 found an over-broad or
mis-filed index:

- Which index splits into which two, and the member reassignment.
- Which member moves from index A to index B.

Present everything together in the garden output shape:

```
curate-grouping — proposal
Scanned: N docs   (M orphans, K existing indexes)
Findings:
  <theme>  — N coherent members, currently ungrouped
  <index-id>  — over-broad: spans "<sub-theme A>" and "<sub-theme B>"
  ...
Proposals:
  [1] Create index "Index: <theme>"  (belongs_to <root/parent-id>)
        members → belongs_to this index:
          <id>  "<title>"  — <one-clause why>
          <id>  "<title>"  — <one-clause why>
  [2] Wire <member-id> "<title>"  →  belongs_to <existing-index-id>
  [3] Split <index-id> into "Index: <A>" + "Index: <B>"; reassign members …
  ...
Awaiting confirmation to apply. Type "apply [1,2,...]" or "apply all" or "skip".
After applying, run summarize-descendants on each affected index to write its
aggregated overview.
```

Do not write anything in this step.

---

## Step 4 — Apply confirmed proposals

Only the proposals the user confirms. Structure changes only — no aggregated
prose here (that is `summarize-descendants`).

Create a new index doc:

```bash
python3 scripts/ldoc.py new \
  --type index \
  --title "Index: <theme>" \
  --level incidental \
  --status living \
  --belongs-to <root-or-parent-index-id> \
  --body "<one-paragraph statement of what this grouping is; the Map section is added by summarize-descendants>"
```

Note the returned id: **INDEX_ID**.

Wire each confirmed member under its index (the member points up via
`belongs_to`):

```bash
python3 scripts/ldoc.py link <member-id> --belongs-to <INDEX_ID>
python3 scripts/ldoc.py history <member-id> --add "curate-grouping: grouped under index <INDEX_ID> (<theme>)"
```

For a recategorization, unlink the old membership first:

```bash
python3 scripts/ldoc.py unlink <member-id> --belongs-to <old-index-id>
python3 scripts/ldoc.py link   <member-id> --belongs-to <new-index-id>
python3 scripts/ldoc.py history <member-id> --add "curate-grouping: moved from index <old-index-id> to <new-index-id>"
```

For a split, create the two new indexes, reassign each member's `belongs_to`,
then retire the over-broad index with a full deprecation (a bare status flip is
invalid — add a `## Correction` section naming the replacements and the
`--superseded-by` edge), mirroring garden's split discipline.

Record a history entry on each new index doc:

```bash
python3 scripts/ldoc.py history <INDEX_ID> --add "curate-grouping: created to group <N> members under <theme>"
```

---

## Step 5 — Hand off to summarize-descendants

Membership is now structure-only; the index bodies do not yet carry their
aggregated overview. For **each** index whose membership changed, the aggregated
`summary` and `## Map` section must be (re)written by the `summarize-descendants`
skill. Either invoke it now (as a **nested invocation** — curate-grouping owns
the episode, so it must not capture its own START or emit its own review summary)
once per affected index, or tell the user to run it. Do not write the Map prose
here yourself — synthesis is that skill's job.

---

## Step 6 — Do NOT reindex; surface the staleness

`hierarchy.md` and `orphans.txt` are now stale (new index, new memberships).
Note this for the user — the orchestrator/reindex run regenerates them. Do not
call `reindex` from this skill.

---

## Step 7 — Validate

```bash
python3 scripts/ldoc.py validate
```

Address any ERRORs before finishing.

---

## Review summary (only if changes were applied; FINAL step)

A pure proposal that wrote nothing emits no summary. If memberships/indexes were
written:

```bash
python3 scripts/ldoc.py review new --since "$START"
```

Report the review id. Review is **post-hoc and non-gating** (see
`review-is-post-hoc`): it records the episode and never blocks the result. If
this skill was invoked as a nested phase by a higher-level orchestrator, skip
this step — the orchestrator owns the single episode summary.
