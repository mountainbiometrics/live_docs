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

The cardinal rule: **two passes, cleanly separated.** Pass 1 is read-only: walk
the full graph, collect all verdicts, and build the complete impact set. Pass 2
is the write pass: apply all `cascade` updates in one coherent batch. Never
interleave reads and writes — applying partial updates mid-walk means each
subsequent verdict is reasoning about an inconsistent intermediate state.

---

## Review-summary rule (read before proceeding)

**Nested invocations do NOT emit their own review summary.** When cascade-check
is called by a higher-level skill (`ingest-reference`, `revise-doc`, `garden`,
`apply-to-docs`), the top-level skill owns the single review summary for the
episode. Duplicate or overlapping review records violate the one-summary-per-episode
principle.

Emit a review summary **only when cascade-check is invoked directly by the
user** (standalone invocation). In that case, capture the start timestamp before
Step 1 and run `python3 scripts/ldoc.py review new --since "<that literal
timestamp>"` as the final step after Step 7/8. See "Step 9" below.

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
date -u +%Y-%m-%dT%H:%M:%SZ
```

Record the literal timestamp it prints (e.g. `2026-06-19T23:48:00Z`); you'll paste this exact value into `review new --since` at the end of the episode.

If this is a **nested invocation** (called from `ingest-reference`, `revise-doc`,
`garden`, or `apply-to-docs`), skip this step entirely — the outer skill owns
the timestamp and will emit the review summary.

---

## PASS 1 — Read-only graph traversal (Steps 1–4)

**No writes occur during Pass 1.** The goal is a complete `verdicts` map over
the entire reachable impact set before a single doc is modified.

---

## Step 1 — Collect neighbors for each changed doc

For each changed doc id, retrieve its full neighbor set:

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
for fresh data.

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

---

## Step 2 — Initialize the cascade session

```
session = {
  "changed":  set of initially changed ids,
  "visited":  empty set,          # ids already processed in this walk
  "verdicts": {}                  # id -> {verdict, reason, neighbor_of, direction}
}
queue = list of initially changed ids
```

The initially-changed docs enter the work queue and are handled by the same BFS
loop as any neighbor (popped, visited, neighbors enumerated in both directions).

---

## Step 3 — Walk the full graph and collect verdicts (read-only BFS)

For each id popped from queue:

1. If already in `session["visited"]`, skip (loop guard).
2. Add to `session["visited"]`.
3. Collect neighbors via `ldoc neighbors <id> --json`; use `requires` and
   `belongs_to` entries (upstream) and their corresponding `dependents`
   (downstream). Skip `relates` and `provenance` entries entirely.
4. For each neighbor `n`:
   - If `n` is already in `session["visited"]`, check the prior verdict: if it
     would be `cascade`, that is a potential **loop** — emit `incompatible` and
     mark that branch halted. Surface to user: "Circular update detected between
     `<id>` and `<n>`." If the prior verdict is `inconsequential`, record and
     continue (no loop conflict).
   - Otherwise, read `docs/<n>.md` and determine a verdict (Step 4).
   - Record the verdict in `session["verdicts"][n]`.
   - If verdict is `cascade` or `incompatible`, add `n` to the queue for further
     traversal (to collect *their* neighbors' verdicts too). Do NOT write yet.
   - If verdict is `inconsequential`: record it, do not enqueue.
   - If verdict is `context-request`: record it, surface to user immediately,
     await answer, then continue traversal with the clarified context.

**Key difference from the old model**: `cascade` verdict enqueues `n` for
further traversal but does NOT trigger a write. All cascade neighbors are
collected into `session["verdicts"]` before any write occurs.

---

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

| Verdict | When | Action in Pass 1 |
|---------|------|--------|
| `inconsequential` | The change in the source doc does not affect the meaning, correctness, or completeness of the neighbor. **This is the norm.** | Record, stop propagation. |
| `cascade` | The neighbor is *living* (`status: living` or `target`), relies on something that changed, and its content is now incorrect, stale, or misleading without an update. | Record, enqueue for neighbor collection. Do NOT write yet. |
| `incompatible` | The change conflicts with something in the neighbor in a way that cannot be resolved without human judgment. | Record, HALT that branch. Surface to user with specifics before proceeding to Pass 2. |
| `context-request` | You cannot determine the impact with confidence from the text alone. | Ask the user one targeted question, await answer, continue. |

**Bias rule**: Prefer `inconsequential` when the relationship is weak or
tangential. Prefer `context-request` over a low-confidence `inconsequential`
— silent drift is worse than a question. Prefer `incompatible` over a guess.

**Descendant-summary rule**: if a changed doc `belongs_to` a descendant-bearing
parent (any `belongs_to` parent, regardless of its `type`), that parent's
aggregated orientation guide is *derived from its members* and is now potentially
stale (the guide may describe the member's old claim). When the member's change
is substantive (title, body, type, status, or membership), emit `cascade` on the
parent. The recommended fix is **not** a hand-patch: re-run the
`summarize-descendants` skill on the parent to re-synthesize its overview. Record
this in the verdict's reason and apply it as the cascade action in Pass 2. (A
purely provenance/relates change to the member does not stale the overview —
prefer `inconsequential`.)

---

## PASS 2 — Batch write (Steps 5–6)

**Before beginning Pass 2**, review the full verdicts map. If any
`incompatible` branches were found, surface them to the user and confirm before
proceeding. Do not write anything until all `incompatible` cases are either
resolved or explicitly accepted by the user.

---

## Step 5 — Apply all cascade updates in one batch

For each doc in `session["verdicts"]` with verdict `cascade` (only valid for
*living* docs):

1. Load the doc to understand its current content:
   ```bash
   python3 scripts/ldoc.py show <n>
   ```
2. Write the doc as its single correct current state, given everything that
   changed across the full impact set. If prior text would now be misleading,
   rewrite it — do not add qualifiers that leave contradictory statements
   coexisting. Make the minimum change that restores consistency, but do not
   mistake "minimum" for "least text" when the prior text was wrong.

   Use `ldoc set` for scalar frontmatter fields, `ldoc link`/`ldoc unlink` for
   edge changes, and direct file editing only for body-text changes:
   ```bash
   # scalar field update
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

3. Record the cascade history entry:
   ```bash
   python3 scripts/ldoc.py history <n> --add "cascade-check: updated because <source-id> changed — <one sentence why>"
   ```

---

## Step 6 — Update the originating doc's history

After the write pass completes, record a history entry on EACH originally-changed
doc summarizing the cascade session outcome:

```bash
python3 scripts/ldoc.py history <changed-id> --add "cascade-check ran: <N> neighbors evaluated — <list each id: verdict>"
```

---

## Step 7 — Surface results to the user

Print a summary table:

```
cascade-check session — changed: [<ids>]
─────────────────────────────────────────────────────
neighbor id    direction    verdict            action taken
20260615...    downstream   cascade            updated body
20260615...    upstream     inconsequential    no change
20260615...    downstream   incompatible       HALTED — <reason>
─────────────────────────────────────────────────────
Total evaluated: N   Cascaded: N   Inconsequential: N   Blocked: N
```

---

## Step 8 — Wide-cascade smell check

If total cascaded docs > 3 from a single routine edit, emit this warning:

> **Design smell**: This cascade touched N docs from a single edit of `<id>`.
> The changed doc may carry more than one responsibility.
> Consider running the `garden` skill (`single-responsibility` pass) on `<id>`.

---

## Step 9 — Generate the review summary (standalone invocations only; FINAL step)

**Skip this step entirely for nested invocations** — when cascade-check is
called from within `ingest-reference`, `revise-doc`, `garden`, or `apply-to-docs`,
the outer skill owns the single episode summary. Emitting one here would create
a duplicate, overlapping review record.

For **standalone invocations only**, after the walk and smell-check are complete:

```bash
python3 scripts/ldoc.py review new --since "2026-06-19T23:48:00Z"   # ← the literal value you recorded at the start
```

After it runs, confirm `touched` is non-empty and reflects the episode's changes.

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

**Pass 1 — Graph traversal:**
1. Start: queue = [20260615090003]
2. Pop 20260615090003, mark visited. Call `ldoc neighbors 20260615090003 --json`.
   Upstream empty, one downstream via `requires`: 20260615100010.
3. Read 20260615100010. Check is_living: `status: living` → eligible.
   - Evaluate: does the "cascade examines `goal` docs" change affect
     20260615100010's content? If 20260615100010 enumerates cascade targets
     → `cascade`. If it just cites the doc as context → `inconsequential`.
   - Suppose: **cascade**. Record in verdicts. Enqueue 20260615100010 for
     neighbor collection (do NOT write yet).
4. Pop 20260615100010. Collect its neighbors. Suppose no new unvisited
     neighbors with cascade verdicts.
5. Queue empty. Pass 1 complete.
   `session["verdicts"]` = {20260615100010: cascade}

**Pass 2 — Batch write:**
6. No `incompatible` cases. Proceed.
7. Apply cascade update to 20260615100010: load it, write the correct current
   state (the cascade-target list now includes `goal`), append history entry.
8. Record originating doc history: `ldoc history 20260615090003 --add
   "cascade-check ran: 1 neighbor evaluated — 20260615100010: cascade"`.
9. Surface table. Total cascaded: 1 — no wide-cascade warning.

**Same scenario but 20260615100010 has `status: deprecated`**: is_living check
fails → verdict is `incompatible` (not `cascade`). Surface to user: "downstream
doc 20260615100010 is deprecated but conflicts with the updated claim — check its
Correction section." Do not rewrite the deprecated doc in Pass 2.

**Same scenario but 5 living dependents all reference the cascade list**: collect
all 5 verdicts in Pass 1, then write all 5 in Pass 2. Wide-cascade warning fires
(N=5 > 3) suggesting a `garden` run.
