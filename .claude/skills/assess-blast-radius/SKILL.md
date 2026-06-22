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
`show` and writes nothing.

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

## Nested-invocation rule (read first)

This skill is **always a nested invocation** — the calling orchestrator owns the
episode. It therefore:

- does NOT capture a `START` time or emit any review summary,
- does NOT write, revise, or create any doc,
- does NOT re-invoke the orchestrator, cascade-check, or any write skill.

It leaves a labeled impact-set map in context for the orchestrator to read.

Because this phase is purely read-only and can be token-heavy on a large graph,
the orchestrator MAY run it in an isolated context via `context: fork` — passing
in the concept/verdict map and receiving only the impact set back. Run inline
(the default) when the orchestrator needs the impact set in the shared window
(e.g. apply-to-docs feeds it directly to synthesis).

---

## Inputs (supplied by the orchestrator)

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

Enqueue neighbors whose verdict is `cascade-extend`, `cascade-full`, or
`conflict-unresolved` for further traversal (to collect *their* neighbors too).
Do not enqueue `inconsequential` neighbors.

---

## Step 2 — Verdict rubric for graph neighbors

Emit exactly one verdict per neighbor:

| Verdict | When |
|---|---|
| `inconsequential` | Neighbor's claim is unaffected by the new intent. The norm. |
| `cascade-extend` | Neighbor is downstream of a changed doc; its content is now stale or misleading and needs revision. |
| `cascade-full` | Neighbor's entire claim is rendered obsolete by the changed upstream. |
| `conflict-unresolved` | Neighbor makes a claim incompatible with the new intent, needing human judgment. |

**Frozen-doc rule**: docs with `status: deprecated` or `status: reference` are
frozen — never mark them `cascade-extend` or `cascade-full`. Mark them
`conflict-unresolved` if their claim now contradicts the new intent, and surface
to the user.

**Bias rule**: prefer `inconsequential` when the relationship is weak or
tangential; prefer `conflict-unresolved` over a low-confidence guess.

---

## Output — the complete impact set

Leave a labeled impact set in context for the orchestrator — every doc that will
need any change, with its verdict, before any write occurs:

```
Impact set (pre-write)
  <id>  "<title>"  verdict: <full-supersession | cascade-full | partial-supersession | cascade-extend | conflict-unresolved | inconsequential>
      Reason: <one sentence>
  ...
Counts: full/cascade-full: N   partial/cascade-extend: N   conflict-unresolved: N   inconsequential: N
```

The orchestrator uses these counts for its pause gate and hands the impact set
to `synthesize-doc-changes`. Do not write anything here.
