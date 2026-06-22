---
name: curate-grouping
description: >
  Survey the live_docs store and PROPOSE how docs should be grouped under
  navigational signpost docs — which coherent themes deserve a descendant-bearing
  signpost, and which docs should `belongs_to` which signpost. This is the agentic
  curation decision: it reads orphans, shared domain/scope, requires/relates
  clusters, and thematic coherence, then proposes new signpost docs and belongs_to
  memberships. Proposal-only — the human confirms before any write, exactly like
  garden. Use when the store has grown enough that navigation needs signposts,
  when orphans accumulate, or when an existing grouping has become too broad and
  should split. A grouping signpost is a curated directory page, NOT an auto-dump.
---

# curate-grouping — Decide what belongs under a grouping signpost (proposal-only)

The cardinal rule: **a grouping signpost is a navigational doc a human would want
to land on** — a "this grouping contains these things" page, like a curated
directory. It is NOT an auto-dump of everything that happens to share a
tag. The judgment here is *editorial*: which groupings are coherent enough to
deserve a signpost, and which doc genuinely belongs under each.

A signpost is **not a special type**. The `index` type has been retired: a doc
earns the navigational-signpost role **structurally**, by having descendants
(incoming `belongs_to` edges), not by declaring a type. A grouping signpost is
typically a `component` (it anchors a structural subsystem), but you pick
whatever type fits the grouping's nature — `requirement`, `principle`, etc. The
member list is derived by consumers (the viewer renders it live from the
`belongs_to` edges); there is no member-list prose stored in the signpost's body.

This skill **proposes** groupings and (only on user confirmation) **applies**
them — it never silently creates signpost docs or rewires `belongs_to` edges. The
same proposal-only discipline as `garden`.

It decides the *structure* (which signposts exist, who belongs to whom). It does
NOT write the aggregated overview prose — that is `summarize-descendants`, run
after the memberships are confirmed.

---

## Episode start time

Before beginning, capture the current UTC time (used only if the pass actually
writes — a pure proposal that writes nothing emits no review summary):

```bash
date -u +%Y-%m-%dT%H:%M:%SZ
```

Record the literal timestamp it prints (e.g. `2026-06-19T23:48:00Z`); you'll paste this exact value into `review new --since` at the end of the episode.

---

## Step 1 — Survey the store for grouping signals

Read, do not write. Gather the inputs an editor would use to spot coherent
groupings:

1. **Existing grouping signposts and their current membership** — so you extend
   rather than duplicate. A signpost is any descendant-bearing doc (a doc that is
   the target of `belongs_to` edges), regardless of type. Read
   `kb/02-docs/.index/hierarchy.md` for the current rollup: it lists each
   descendant-bearing doc and the children that hard-edge into it. Cross-check a
   candidate parent's live membership with:
   ```bash
   ldoc neighbors <id> --kind dependents --json
   ```
2. **Orphans** — docs outside the `belongs_to` hierarchy are the prime
   candidates for a home. Query them FRESH (single source of truth, computed
   live — not a stale cache):
   ```bash
   ldoc orphans
   ```
   This is pure `belongs_to` in/out topology with no type exemptions; apply your
   own judgment (e.g. `reference`/`type` docs are legitimately edge-light and not
   curation targets).
3. **Shared `domain` / `scope`** — docs tagged into the same area are a thematic
   cluster signal:
   ```bash
   ldoc find --domain "<domain>" --json
   ldoc find --scope "<scope>" --json
   ```
4. **`requires` / `relates` clusters** — docs that depend on or see-also each
   other form natural neighborhoods:
   ```bash
   ldoc neighbors <id> --json
   ldoc graph <id> --depth 2 --direction both --json
   ```
5. **Full inventory** for thematic coherence — skim titles/types to recognize a
   theme text search would miss:
   ```bash
   ldoc ls --json
   ```

---

## Step 2 — Judge which groupings deserve a signpost

A signal cluster is not automatically a grouping. Apply editorial judgment:

**When a grouping signpost SHOULD exist:**

- Several living docs share a coherent theme a reader would navigate to as a
  unit ("everything about the cascade engine", "the edge-typing decisions"), AND
- a person landing on a "this grouping contains these things" page would find it
  genuinely useful as a starting point, AND
- the grouping has enough members (≈3+) to be worth a signpost — two docs that
  already `relate` to each other do not need a grouping.

**When a grouping should NOT exist (leave the docs as-is):**

- The "theme" is just a shared tag with no narrative throughline — that is what
  `find --domain` is for; do not reify every tag as a grouping.
- The members are better expressed as a `requires`/`relates` cluster than a
  parent/child hierarchy.
- A single doc would be the only member.

**When an existing grouping is TOO BIG and should split:**

- Its members span more than one coherent sub-theme — a reader scanning the
  derived member list would not perceive one subject. Propose splitting into two
  narrower groupings, each a tighter signpost, and reassign each member to the
  right one.
- Symptom: you would describe the grouping as "X and also Y."

**When a doc is MISCATEGORIZED:**

- A member's subject does not match the grouping's theme — propose moving its
  `belongs_to` to a better-fitting signpost (or removing the membership if none
  fits and the doc stands alone).

**Bias rule:** prefer *fewer, tighter* groupings. A signpost that tries to hold
everything is navigation noise. Prefer leaving a doc ungrouped over forcing it
under a loosely-related signpost — a wrong grouping misleads a navigator worse
than no grouping does.

---

## Step 3 — Compose the proposal

For each grouping decision, propose concretely. Two kinds of proposal:

**(a) New signpost doc** for a coherent theme that lacks one:

- The `type` that fits the grouping's nature — typically `component` (it anchors
  a structural subsystem), but pick whatever the grouping actually is
  (`requirement`, `principle`, …). It is NOT a special `index` type; it becomes a
  signpost structurally, by acquiring descendants.
- Suggested title — just the theme itself (e.g. "Foundational Principles"); the
  type is prepended automatically at display time. Plus a short `label`.
- One-line statement of what the grouping is — the editorial throughline that
  makes these docs one subject.
- The list of member ids that would `belongs_to` it.
- Its place in the hierarchy: does it `belongs_to` the root component
  (`20260615090011`) or a broader signpost?

**(b) `belongs_to` membership wiring** for existing docs (including orphans)
into an existing or proposed signpost:

- Member id → target signpost id, with a one-clause reason it belongs.

**(c) Split / recategorize** proposals where Step 2 found an over-broad or
mis-filed grouping:

- Which signpost splits into which two, and the member reassignment.
- Which member moves from signpost A to signpost B.

Present everything together in the garden output shape:

```
curate-grouping — proposal
Scanned: N docs   (M orphans, K existing signposts)
Findings:
  <theme>  — N coherent members, currently ungrouped
  <signpost-id>  — over-broad: spans "<sub-theme A>" and "<sub-theme B>"
  ...
Proposals:
  [1] Create signpost "<type>: <theme>"  (belongs_to <root/parent-id>)
        members → belongs_to this signpost:
          <id>  "<title>"  — <one-clause why>
          <id>  "<title>"  — <one-clause why>
  [2] Wire <member-id> "<title>"  →  belongs_to <existing-signpost-id>
  [3] Split <signpost-id> into "<type>: <A>" + "<type>: <B>"; reassign members …
  ...
Awaiting confirmation to apply. Type "apply [1,2,...]" or "apply all" or "skip".
After applying, run summarize-descendants on each affected signpost to write its
aggregated overview.
```

Do not write anything in this step.

---

## Step 4 — Apply confirmed proposals

Only the proposals the user confirms. Structure changes only — no aggregated
prose here (that is `summarize-descendants`).

Create a new signpost doc — use the type that fits the grouping (typically
`component`):

```bash
ldoc new \
  --type <fitting-type> \
  --title "<theme>" \
  --level incidental \
  --status living \
  --belongs-to <root-or-parent-signpost-id> \
  --body "<one-paragraph statement of what this grouping is; the orientation guide is written by summarize-descendants>"
```

Note the returned id: **SIGNPOST_ID**. It becomes a signpost the moment members
point up into it — no special type flag.

Wire each confirmed member under its signpost (the member points up via
`belongs_to`):

```bash
ldoc link <member-id> --belongs-to <SIGNPOST_ID>
ldoc history <member-id> --add "curate-grouping: grouped under <SIGNPOST_ID> (<theme>)"
```

For a recategorization, unlink the old membership first:

```bash
ldoc unlink <member-id> --belongs-to <old-signpost-id>
ldoc link   <member-id> --belongs-to <new-signpost-id>
ldoc history <member-id> --add "curate-grouping: moved from <old-signpost-id> to <new-signpost-id>"
```

For a split, create the two new signposts, reassign each member's `belongs_to`,
then retire the over-broad signpost with a full deprecation (a bare status flip
is invalid — add a `## Correction` section naming the replacements and the
`--superseded-by` edge), mirroring garden's split discipline.

Record a history entry on each new signpost doc:

```bash
ldoc history <SIGNPOST_ID> --add "curate-grouping: created to group <N> members under <theme>"
```

---

## Step 5 — Hand off to summarize-descendants

Membership is now structure-only; the signpost bodies do not yet carry their
aggregated overview. For **each** signpost whose membership changed, the
aggregated `summary` and orientation-guide body must be (re)written by the
`summarize-descendants` skill. Either invoke it now (as a **nested invocation** —
curate-grouping owns the episode, so it must not capture its own START or emit
its own review summary) once per affected signpost, or tell the user to run it.
Do not write the orientation guide here yourself — synthesis is that skill's job.
(There is no member-list prose to write; the viewer derives the member list live
from the `belongs_to` edges.)

---

## Step 6 — Do NOT reindex; surface the staleness

`hierarchy.md` is now stale (new signpost, new memberships — it rolls up children
under every descendant-bearing doc). Note this for the user
— the orchestrator/reindex run regenerates it. Do not call `reindex` from this
skill. (Orphan status is not a cached artifact — `ldoc orphans` always computes
it fresh, so there is nothing to regenerate there.)

---

## Step 7 — Validate

```bash
ldoc validate
```

Address any ERRORs before finishing.

---

## Review summary (only if changes were applied; FINAL step)

A pure proposal that wrote nothing emits no summary. If memberships/indexes were
written:

```bash
ldoc review new --since "2026-06-19T23:48:00Z"   # ← the literal value you recorded at the start
```

After it runs, confirm `touched` is non-empty and reflects the episode's changes.

Report the review id. Review is **post-hoc and non-gating** (see
`review-is-post-hoc`): it records the episode and never blocks the result. If
this skill was invoked as a nested phase by a higher-level orchestrator, skip
this step — the orchestrator owns the single episode summary.
