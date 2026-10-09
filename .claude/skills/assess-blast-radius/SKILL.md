---
name: assess-blast-radius
user-invocable: false
description: >
  Given the mapped concepts and their directly-affected docs, walk the
  dependency graph BEFORE any write to determine the complete impact set —
  every doc that will need a change, with a verdict. This is the pre-write
  impact survey: read-only BFS over requires/belongs_to (upstream) and
  dependents (downstream), with the frozen-doc rule applied. Distinct from the
  post-write cascade-check, but uses the same graph-walk discipline. A phase
  sub-skill, not meant to be run directly by a user.
---

# assess-blast-radius — Pre-write impact survey (shared phase)

This skill owns the **pre-write** graph walk: starting from the directly-matched
docs, it expands outward to find every doc the new intent will touch, and
returns a complete impact set with verdicts — **before a single byte is
written**. It is invoked after `map-concepts-to-docs` by orchestrators that want
to know the full blast radius before deciding whether to pause and what to
synthesize.

**This entire skill is read-only.** It issues only `ldoc neighbors`/`graph`/
`show`, writes nothing, and does no episode bookkeeping (no `START`, no review).
It says nothing about what happens next — whoever invoked it resumes with the
impact set in context.

---

## Relationship to cascade-check (read this)

`assess-blast-radius` and `cascade-check` walk the same graph with the same
verdict discipline, but at opposite ends of an episode:

- **assess-blast-radius is the read-only PRE-write survey.** It runs from the
  *mapped* concepts before any doc is changed, so the orchestrator can warn on a
  large radius and so `synthesize-doc-changes` has the full picture in view. It
  never writes.
- **cascade-check is the POST-write propagation.** It runs from docs that have
  *already* changed and applies cascade updates to their neighbors (its Pass 2).

They are complementary, not redundant: this skill answers "what will this touch
if I proceed?"; cascade-check answers "now that these docs changed, what else
must be fixed?" An orchestrator that surveys the radius here may still invoke
cascade-check after writing (revise-doc does), or may fold synthesis into one
batch from this impact set (apply-to-docs does).

---

## Inputs

- **The relationship verdict map** from `map-concepts-to-docs` — the directly-
  matched docs and their relationships.
- **The change description** — what the new intent asserts (richer context
  produces more reliable verdicts).

---

## Step 1 — Walk the graph from every non-compatible match

The verdict map identifies direct matches. Expand it by walking the dependency
graph from every directly-matched doc whose relationship is **not**
`compatible`. Use a visited set so each node is walked once (cycle safety).

For each such doc:

```bash
ldoc neighbors <id> --json
```

This returns `{requires, belongs_to, dependents, relates, provenance}`. Walk
only `requires`/`belongs_to` (upstream) and `dependents` (downstream) — the hard
cascade edges. Skip `relates` and `provenance` (soft navigation edges).

If you want the full two-hop picture up front:

```bash
ldoc graph <id> --depth 2 --direction both --json
```

For each neighbor not yet in the map, load it and assess whether the new intent
affects it:

```bash
ldoc show <neighbor-id>
```

Judge an upstream neighbor (`requires`/`belongs_to`) by its title and summary,
not only its body: the title and summary are the claim its dependents read.
When the new intent extends or contradicts them, the verdict is
`cascade-extend` or `cascade-full`, and the revision covers the title.

Enqueue neighbors whose verdict is `cascade-extend`, `cascade-full`, or
`conflict-unresolved` for further traversal (to collect *their* neighbors too).
Do not enqueue `inconsequential` neighbors.

---

## Step 2 — Verdict rubric for graph neighbors

Emit exactly one verdict per neighbor:

| Verdict | When |
|---|---|
| `inconsequential` | Neighbor's claim is unaffected by the new intent. The norm. |
| `cascade-extend` | Neighbor is downstream of a changed doc, or upstream with a title or summary the new intent extends or contradicts; its content is now stale or misleading and needs revision. |
| `cascade-full` | Neighbor's entire claim is rendered obsolete by the changed upstream. |
| `conflict-unresolved` | The neighbor states the same claim at a higher intent than the change carries, or is frozen — apply `_shared/conflict-test.md` first. Its assertion is left and the new claim is written beside it. A neighbor that only records the prior design is `cascade-extend` / `cascade-full`. |

**Frozen-doc rule**: docs with `status: deprecated` or `status: reference` are
frozen — never mark them `cascade-extend` or `cascade-full`. Mark them
`conflict-unresolved` if their claim now contradicts the new intent, and surface
to the user.

**Intent comparison**: `_shared/conflict-test.md` maps the comparison in
`_shared/facets.md` onto these verdicts. A `conflict-unresolved` entry never
blocks the rest of the impact set.

**Bias rule**: prefer `inconsequential` when the relationship is weak or
tangential; when unsure whether a neighbor is the same claim, read it
(`ldoc show`) rather than guessing either way.

---

## Output — the complete impact set

Emit a labeled impact set — every doc that will need any change, with its
verdict, before any write occurs:

```
Impact set (pre-write)
  [<Intent> <type>: <Title>](<url>)  verdict: <full-supersession | cascade-full | partial-supersession | cascade-extend | conflict-unresolved | inconsequential>
      Reason: <one sentence>
  ...
Counts: full/cascade-full: N   partial/cascade-extend: N   conflict-unresolved: N   inconsequential: N
```
