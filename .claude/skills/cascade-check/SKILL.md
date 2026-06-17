---
name: cascade-check
description: >
  After one or more docs change, walk the dependency graph in BOTH directions
  (upstream dependencies and downstream dependents) and decide whether each
  neighbor must be updated, is unaffected, conflicts, or needs clarification.
  Use this skill whenever a doc is edited and you need to know what else may
  have been invalidated. It is the primary consistency-enforcement mechanism
  for the live_docs store.
---

# cascade-check — Propagate or halt consistency across the dependency graph

## Review-summary rule (read before proceeding)

**Nested invocations do NOT emit their own review summary.** When cascade-check
is called by a higher-level skill (`ingest-reference`, `revise-doc`, `garden`),
the top-level skill owns the single review summary for the episode. Duplicate or
overlapping review records violate the one-summary-per-episode principle.

Emit a review summary **only when cascade-check is invoked directly by the
user** (standalone invocation). In that case, capture `START` before Step 1 and
run `python3 scripts/ldoc.py review new --since "$START"` as the final step
after Step 7/8. See "Step 9" below.

Review is **post-hoc and non-gating** (see `review-is-post-hoc`): the summary
records the episode for later review/signoff and never blocks the cascade.

---

## Inputs

- **Changed doc id(s)** — one or more `docs/<id>.md` filenames (without `.md`).
  If not given, check `git diff --name-only` (if a git repo) to find recently
  modified docs; if that yields nothing, ask the user which doc changed.
- **Change description** (optional but strongly preferred) — a plain-language
  summary of what changed and why. Richer context produces more reliable verdicts.
- **Invocation context** — **standalone** (user called cascade-check directly)
  or **nested** (called from another skill). Default: standalone.

## Step 0 — Capture start time (standalone invocations only)

If this is a **standalone invocation** (user called cascade-check directly, not
from within another skill), capture the episode start time before doing anything
else:

```bash
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

If this is a **nested invocation** (called from `ingest-reference`, `revise-doc`,
or `garden`), skip this step entirely — the outer skill owns the timestamp and
will emit the review summary.

---

## Step 1 — Collect neighbors for each changed doc (fresh, every time)

For each changed doc id, retrieve its full neighbor set using:

```bash
python3 scripts/ldoc.py neighbors <id> --json
```

This returns `{requires, belongs_to, provenance, relates, dependents, referenced_by}` — all
resolved to `{id, label, display}` entries. Use `requires` and `belongs_to`
(upstream) and their `dependents` (downstream) for the cascade walk. `relates`
and `provenance` edges are navigation-only and do NOT cascade.

**Which edges cascade:** only `requires` and `belongs_to` are hard edges that
cascade in both directions. `relates` and `provenance` are soft navigation edges
— never walked for cascade. When a doc becomes `deprecated`, its reverse
`requires`/`belongs_to` dependents must still be cascade-checked (they now
depend on something that no longer holds).

Do not read from `docs/.index/dependents.json` — always call `ldoc neighbors`
for fresh data. At this scale a full scan takes milliseconds and avoids
stale-cache errors.

If you need the full two-hop picture before starting, use:

```bash
python3 scripts/ldoc.py graph <id> --depth 2 --direction both --json
```

To surface dangling edges across the whole store before proceeding, run:

```bash
python3 scripts/ldoc.py edges --json
```

and check the `dangling` key. Surface any reported dangling edges to the user
before proceeding.

## Step 2 — Initialize the cascade session

```
session = {
  "changed":  set of initially changed ids,
  "visited":  empty set,          # ids already processed in this walk
  "verdicts": {}                  # id -> {verdict, reason, neighbor_of}
}
queue = list of initially changed ids
```

The initially-changed docs are not pre-processed separately; they enter the work
queue and are handled by the same BFS loop as any neighbor (popped, visited,
neighbors enumerated in both directions).

## Step 3 — Walk the graph (BFS)

For each id popped from queue:

1. If already in `session["visited"]`, skip (loop guard).
2. Add to `session["visited"]`.
3. Collect neighbors via `ldoc neighbors <id> --json`; use `requires` and
   `belongs_to` entries (upstream) and their corresponding `dependents`
   (downstream). Skip `relates` and `provenance` entries entirely.
4. For each neighbor `n`:
   - If `n` is already in `session["visited"]`, check the verdict: if it would be
     `cascade`, that is a **loop** — emit `incompatible` and HALT that branch.
     Surface to user: "Circular update detected between `<id>` and `<n>`." If the
     verdict is `inconsequential`, simply record it and continue (no loop conflict).
     This guards against genuine cascade-back contradictions while allowing
     inconsequential re-encounters.
   - Otherwise, read `docs/<n>.md` and make a verdict (see Step 4).
   - Record the verdict in `session["verdicts"][n]`.
   - If verdict is `cascade`: apply the update (Step 5), add `n` to queue.
   - If verdict is `inconsequential`: stop propagation down this edge.
   - If verdict is `incompatible` or `context-request`: stop that branch,
     surface to user immediately.

## Step 4 — Verdict rubric

**is_living check first.** Before issuing any verdict, check the neighbor's
`status`:
- `status: living` or `status: target` — the doc is *living* and may be
  rewritten to track new reality. Apply verdicts normally.
- `status: deprecated` or `status: reference` — the doc is *frozen*. Cascade-
  check may still flag it as `incompatible` (to surface the conflict to the
  user), but it is **never rewritten** to track current state. The only allowed
  edit to a deprecated doc is refining its `## Correction` section or adding a
  `superseded_by` edge. Skip `cascade` verdicts for frozen docs; emit
  `incompatible` instead and surface to user.

Emit exactly one verdict per neighbor edge:

| Verdict | When | Action |
|---------|------|--------|
| `inconsequential` | The change in the source doc does not affect the meaning, correctness, or completeness of the neighbor. **This is the norm.** | Stop propagation. |
| `cascade` | The neighbor is *living* (`status: living` or `target`), relies on something that changed, and its content is now incorrect, stale, or misleading without an update. | Update neighbor (Step 5), enqueue it. |
| `incompatible` | The change conflicts with something in the neighbor in a way that cannot be resolved without human judgment — e.g., contradictory constraints, a second update to a doc already updated in this session, or a *frozen* doc whose claim is now contradicted. | HALT that branch, surface to user with specifics. |
| `context-request` | You cannot determine the impact with confidence from the text alone. | Ask the user one targeted question rather than defaulting silently to `inconsequential`. |

**Bias rule**: Prefer `inconsequential` when the relationship is weak or
tangential. Prefer `context-request` over a low-confidence `inconsequential`
— silent drift is worse than a question. Prefer `incompatible` over a guess.

**Direction note**: Both upstream (things this doc requires or belongs_to) and
downstream (things that require or belong_to this doc) neighbors must be
evaluated. Upstream neighbors need checking because the changed doc may now
violate or contradict something it was supposed to conform to. Downstream
neighbors need checking because they cited this doc for something that has now
changed.

## Step 5 — Apply a cascade update

When the verdict is `cascade` (only valid for *living* docs — `status: living`
or `status: target`):

1. Load the doc to understand its current content:
   ```bash
   python3 scripts/ldoc.py show <n>
   ```
2. Make the minimum change needed to restore consistency. Use `ldoc set` for
   scalar frontmatter fields, `ldoc link`/`ldoc unlink` for edge changes, and
   direct file editing only for body-text changes that have no `ldoc` verb:
   ```bash
   # scalar field update (use new status values: living, target, deprecated, reference)
   python3 scripts/ldoc.py set <n> --status deprecated
   # edge updates
   python3 scripts/ldoc.py link <n> --requires <new-dep-id>
   python3 scripts/ldoc.py link <n> --belongs-to <parent-id>
   python3 scripts/ldoc.py link <n> --superseded-by <replacement-id>
   ```
   **Deprecation rule**: if restoring consistency means deprecating the doc,
   a bare `--status deprecated` is insufficient. You MUST also add a
   `## Correction` section to the body explaining why the doc is now wrong and
   which doc supersedes it, then add the `--superseded-by` edge. Only after
   both are in place is the deprecation complete.
   Do not refactor or rewrite beyond what the cascade requires.
3. Record the cascade history entry:
   ```bash
   python3 scripts/ldoc.py history <n> --add "cascade-check: updated because <source-id> changed — <one sentence why>"
   ```

## Step 6 — Update the originating doc's history

After the walk completes, record a history entry on EACH originally-changed doc
summarizing the cascade session outcome:

```bash
python3 scripts/ldoc.py history <changed-id> --add "cascade-check ran: <N> neighbors evaluated — <list each id: verdict>"
```

## Step 7 — Surface results to the user

Print a summary table:

```
cascade-check session — changed: [<ids>]
─────────────────────────────────────────────────────
neighbor id    direction    verdict            action taken
20260615...    downstream   cascade            updated history entry
20260615...    upstream     inconsequential    no change
20260615...    downstream   incompatible       HALTED — <reason>
─────────────────────────────────────────────────────
Total evaluated: N   Cascaded: N   Inconsequential: N   Blocked: N
```

## Step 8 — Wide-cascade smell check

If total cascaded docs > 3 from a single routine edit, emit this warning:

> **Design smell**: This cascade touched N docs from a single edit of `<id>`.
> The changed doc may carry more than one responsibility.
> Consider running the `garden` skill (`single-responsibility` pass) on `<id>`.

---

## Step 9 — Generate the review summary (standalone invocations only; FINAL step)

**Skip this step entirely for nested invocations** — when cascade-check is
called from within `ingest-reference`, `revise-doc`, or `garden`, the outer
skill owns the single episode summary. Emitting one here would create a
duplicate, overlapping review record.

For **standalone invocations only**, after the walk and smell-check are complete:

```bash
python3 scripts/ldoc.py review new --since "$START"
```

Report the returned review id to the user:

```
Review summary created: <id>   (reviews/<id>.md)
```

Review is post-hoc and non-gating: this never blocks the cascade result.

---

## Worked example

**Scenario**: `20260615090003.md` (Type: decision, status: living) is edited —
its "Cascade Behavior" section is updated to say cascade should also examine
`goal` docs.

**Neighbors of 20260615090003** (from `ldoc neighbors 20260615090003 --json`):
`requires: []` (none upstream), `dependents: [{id: "20260615100010", ...}]`
(one downstream — a decision doc that lists 20260615090003 in its `requires`).

**Walk**:

1. Start: queue = [20260615090003]
2. Pop 20260615090003, mark visited. Call `ldoc neighbors 20260615090003 --json`.
   Upstream empty, one downstream via `requires`: 20260615100010.
3. Check is_living for 20260615100010: `status: living` → eligible for cascade.
   Evaluate 20260615100010 (downstream). Load it with `ldoc show 20260615100010`:
   - Read it. Its content references the decision type's cascade rules.
   - The change adds `goal` to the cascade list. Does 20260615100010 enumerate
     cascade targets? If yes — the list is now stale → **cascade**.
   - If no, it just cites the doc as context → **inconsequential**.
4. Suppose verdict: **inconsequential**. Record it. Stop.
5. Walk complete. Record history: `ldoc history 20260615090003 --add "cascade-check ran: 1 neighbor evaluated — 20260615100010: inconsequential"`. Surface table.
6. Total cascaded: 0 → no wide-cascade warning.

**Same scenario but 20260615100010 has `status: deprecated`**: is_living check
fails → verdict is `incompatible` (not `cascade`). Surface to user: "downstream
doc 20260615100010 is deprecated but conflicts with the updated claim — check its
Correction section." Do not rewrite the deprecated doc.

**Same scenario but 5 living dependents all reference the cascade list**: cascade
fires on all 5, triggering the wide-cascade smell warning suggesting a `garden` run.
