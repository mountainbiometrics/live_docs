---
name: garden-hierarchy
user-invocable: false
description: >
  Gardening phase: tree structure — orphan homes, grouping signposts, scope
  anchors, re-scoping overgrown branches, and placement refinement. Absorbs
  curate-grouping plus garden tag-curation Part A. Reports signposts whose
  membership changed for the dispatcher to summarize once at episode close.
  Nested phase; garden dispatcher owns the episode.
---

# garden-hierarchy — Tree placement, scope, and navigability (structure phase)

**Contract:** nested phase only. Capture no START, run no `cascade-check`, emit
no review. Do **not** invoke `garden-summarize` here — report signpost ids whose
membership or scope changed in `Signposts-changed:`; the dispatcher summarizes
them once after all phases (before cascade-check).

**Placement policy:** read and apply
`.claude/skills/_shared/belongs-to-placement.md` verbatim — the authoritative
refiner with full-store context.

Tree navigability and placement correctness are independent axes: every child can be correctly placed while a branch is still a navigability failure.

---

## Part A — Grouping / orphan homes

*(Former `curate-grouping`.)*

A signpost is a **curated directory**, not an auto-dump. Prefer fewer, tighter
groupings. Signposts are structural (descendant-bearing), not a special type.

### A1 — Survey (read-only)

```bash
ldoc orphans
ldoc ls --json
ldoc neighbors <id> --kind dependents --json   # per existing signpost
ldoc find --domain "<domain>" --json             # cluster signals
ldoc graph <id> --depth 2 --direction both --json
```

Check the hierarchy index (`<docs>/.index/hierarchy.md`, where `<docs>` is the configured docs store path) for a rollup cross-check; it may be stale until `ldoc reindex` is run.

### A2 — Judge

Create signposts when ≈3+ docs share a coherent navigable theme. Do NOT reify
every tag. Split over-broad signposts ("X and also Y"). Move miscategorized
members. Leave ungrouped rather than force a bad home.

### A3 — Apply structure

Read and apply `.claude/skills/_shared/label-title-summary.md` — `--label` is required and must name the subject (not a fragment); `--title` is optional.

```bash
ldoc new --type component --label "<2–5 word Title-Case handle>" [--title "<theme>"] --belongs-to <parent> --body "…"
ldoc link <member-id> --belongs-to <SIGNPOST_ID>
ldoc history <member-id> --add "garden-hierarchy: grouped under <SIGNPOST_ID>"
```

Recategorize: `ldoc unlink` old + `ldoc link` new. Split: create narrower
signposts, reassign, deprecate over-broad signpost with `## Correction` +
`--superseded-by`.

---

## Part B — Scope anchors

*(Former garden Pass 5 Part A.)*

Scope is a topology-derived facet: set on an "anchor" doc, it applies to that doc and its entire `belongs_to` subtree; effective scope is the union of `scope` values along the full `belongs_to` genealogy. Most docs inherit; only anchor docs (typically `component`) explicitly declare a `scope` value. Find descendant-bearing structural docs (typically `component`) that should declare a distinct `scope` anchor:

- Bears descendants but declares **no** own `scope` (inherits coarser parent
  zone the subtree should specialize), **or**
- Declares `scope` **identical to parent's** (redundant restatement).

Propose slug from doc role; apply:
```bash
ldoc set <id> --scope <anchor-name>
ldoc history <id> --add "garden-hierarchy: set scope anchor <anchor-name>"
```

Leave root alone.

---

## Part C — Re-scoping overgrown branches

*(New.)*

**Master criterion: navigability.** A reader must be able to scan a signpost's direct children and orient. That is what you are preserving or restoring; the count is only a proxy.

**≈12 direct children** is a trigger to *examine* the branch, not a reason to
split it. When you find a branch over this threshold:

- **Split** only if the children genuinely cluster into coherent sub-themes AND
  the flat list is actually hard to scan. A well-named, internally coherent list
  of 14 siblings is fine — do not split it just to be under 12.
- **Do not split** a clean, scannable list of well-named siblings solely because
  the count exceeds 12.
- **Do examine** an under-12 branch whose children span incoherent sub-themes —
  navigability can fail below the threshold too.
- **Do not manufacture a deep skinny tree** of 3-child intermediate nodes just
  to reduce fan-out. A chain of shallow signposts (one hop per level) adds hops
  without adding orientation — equally un-navigable in the other direction.

Navigability is also the master of Part A's "prefer fewer, tighter groupings" —
both rules serve the same goal: a reader can scan and orient at each level.

When splitting is warranted:
1. Cluster direct children by sub-theme.
2. Create intermediate signposts one level down; re-home children via `belongs_to`.
3. Recurse if a new signpost is still hard to scan (rare).

This is the structural analogue of decompose: "in the tree" ≠ navigable tree.

Do **not** call `reindex` — note staleness of `hierarchy.md` for the user.
Do **not** invoke `garden-summarize` — list affected signpost ids in output.

---

## Part D — Mental-model restructuring

*(New.)*

The `belongs_to` hierarchy is the **system's mental model** — generally mirroring
code but a hybrid; placement carries scope; kept roughly balanced. The *what/why*
of good vs bad placement (group by what docs are about not where they came from;
shared concepts belong at a shared parent; one label spanning scopes is
mis-scoped) lives in `_shared/belongs-to-placement.md`, "What groups well, what
doesn't" — read it; this part does not re-explain it. Parts A–C keep the tree
*navigable*; Part D corrects branches that are navigable yet *wrong about the
system*. Each signal below names the shared definition it detects, then gives the
full-store-pass detection and the remediation.

### D1 — Provenance cluster vs real structural node

**Detect.** The "group by what, not where they came from" trap (shared file). On a
full-store pass, flag any signpost whose children are heterogeneous by topic but
homogeneous by `provenance`/source under a generic "Guide:"/"Notes:"/"<Source>
docs" label. `ldoc ls --json` for labels; `ldoc neighbors <id> --kind dependents`
+ child `provenance` to confirm the children share a source but span themes.

**Remediate.** **Dissolve** it: for each child, find the real structural parent by
topic and `ldoc link --belongs-to` it there; where the real node does not yet
exist, create it (Part A) and re-home. When the signpost is emptied, deprecate it
(`## Correction` + `--superseded-by` the dominant new home, or unlink-and-retire
if it fragments across several).

### D2 — Lift shared cluster up

**Detect.** The "shared concept belongs at a shared parent" trap (shared file). On
a full-store pass, flag a cluster filed under one subsystem whose
`ldoc neighbors <id> --kind dependents` and `requires` web show inbound edges from
two or more *sibling* subsystems, not just its parent. A single inbound edge is a
`requires`, not a lift — lift only when one-sibling membership misleads about the
concept's reach.

**Remediate.** **Lift to a shared parent** — the nearest ancestor that contains
all referencing siblings (create one per Part A if absent). `ldoc unlink` from the
implementation subsystem, `ldoc link --belongs-to` the shared parent, and set a
scope anchor there if the lift creates a new shared zone (Part B).

### D3 — One label spans multiple scopes → split + re-home

**Detect.** The "one label spanning scopes is mis-scoped" trap (shared file). On a
full-store pass, flag a label/concept you cannot give one coherent scope anchor or
summary without equivocating — a single label that means materially different
things in different parts of the system (so its one summary has to hedge across
all of them).

**Remediate.** The atomic *split* is **garden-decompose's** job — refer the
overloaded doc there, do not duplicate it. garden-hierarchy then **re-homes and
re-scopes** the resulting pieces: place each under the structural parent for its
scope (Part A) and re-scope its anchor to that zone (Part B), so each lands where
its scope actually binds.

Each of D1–D3 changes membership or scope — report the affected signpost ids in
`Signposts-changed:` as elsewhere. Do **not** call `reindex` or
`garden-summarize`; the dispatcher owns cascade and summary.

---

## Output

```
garden — phase: hierarchy
Scanned: N docs (M orphans, K signposts)
Findings:
  …
Actions:
  …
Applied: [list]
Changed-ids: [id, …]
Signposts-changed: [signpost-id, …]   # membership or scope changed — dispatcher summarizes once
```
