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

## Inputs

- **Changed doc id(s)** — one or more `docs/<id>.md` filenames (without `.md`).
  If not given, check `git diff --name-only` (if a git repo) to find recently
  modified docs; if that yields nothing, ask the user which doc changed.
- **Change description** (optional but strongly preferred) — a plain-language
  summary of what changed and why. Richer context produces more reliable verdicts.

## Step 1 — Build the reverse-edge map (fresh, every time)

Run the shared CLI to get fresh, authoritative forward and reverse maps:

```bash
python3 scripts/edges.py --json
```

This outputs a JSON object with keys `forward`, `reverse`, `titles`, and
`dangling`. Parse it to obtain:

```
forward[id]  = list of ids this doc depends on
reverse[id]  = list of ids that depend on this doc
```

Do not read from `docs/.index/dependents.json` — always call `edges.py --json`
for fresh maps. At this scale a full scan takes milliseconds and avoids
stale-cache errors. If any `dangling` edges are reported, surface them to the
user before proceeding.

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
3. Collect neighbors: `forward[id]` ∪ `reverse[id]`.
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

Emit exactly one verdict per neighbor edge:

| Verdict | When | Action |
|---------|------|--------|
| `inconsequential` | The change in the source doc does not affect the meaning, correctness, or completeness of the neighbor. **This is the norm.** | Stop propagation. |
| `cascade` | The neighbor references or relies on something that changed, and its content is now incorrect, stale, or misleading without an update. | Update neighbor (Step 5), enqueue it. |
| `incompatible` | The change conflicts with something in the neighbor in a way that cannot be resolved without human judgment — e.g., contradictory constraints, or this would be the second update to a doc already updated in this session. | HALT that branch, surface to user with specifics. |
| `context-request` | You cannot determine the impact with confidence from the text alone. | Ask the user one targeted question rather than defaulting silently to `inconsequential`. |

**Bias rule**: Prefer `inconsequential` when the relationship is weak or
tangential. Prefer `context-request` over a low-confidence `inconsequential`
— silent drift is worse than a question. Prefer `incompatible` over a guess.

**Direction note**: Both upstream (things this doc depends on) and downstream
(things that depend on this doc) neighbors must be evaluated. Upstream neighbors
need checking because the changed doc may now violate or contradict something it
was supposed to conform to. Downstream neighbors need checking because they cited
this doc for something that has now changed.

## Step 5 — Apply a cascade update

When the verdict is `cascade`:

1. Read `docs/<n>.md`.
2. Make the minimum change needed to restore consistency. Edit the body and/or
   frontmatter field(s) that are now stale. Do not refactor or rewrite beyond
   what the cascade requires.
3. Append a `history` entry to the doc (this is a genuine change, not a creation):
   ```yaml
   - at: "<ISO 8601 UTC timestamp>"
     summary: "cascade-check: updated because <source-id> changed — <one sentence why>"
   ```
   If `history:` is currently `history: []`, replace it with a block-sequence
   form:
   ```yaml
   history:
     - at: "<ISO 8601 UTC timestamp>"
       summary: "cascade-check: updated because <source-id> changed — <one sentence why>"
   ```
4. Write the file back.

## Step 6 — Update the originating doc's history

After the walk completes, append a `history` entry to EACH originally-changed doc
summarizing the cascade session outcome:

```yaml
- at: "<timestamp>"
  summary: "cascade-check ran: <N> neighbors evaluated — <list each id: verdict>"
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

## Worked example

**Scenario**: `20260615090003.md` (Type: decision) is edited — its "Cascade
Behavior" section is updated to say cascade should also examine `goal` docs.

**Forward edges of 20260615090003**: `depends_on: []` (none)
**Reverse edges** (who depends on 20260615090003): suppose `20260615100010.md`
(a decision doc) lists `20260615090003` in its `depends_on`.

**Walk**:

1. Start: queue = [20260615090003]
2. Pop 20260615090003, mark visited. Neighbors: none forward, one reverse
   (20260615100010).
3. Evaluate 20260615100010 (downstream):
   - Read it. Its content references the decision type's cascade rules.
   - The change adds `goal` to the cascade list. Does 20260615100010 enumerate
     cascade targets? If yes — the list is now stale → **cascade**.
   - If no, it just cites the doc as context → **inconsequential**.
4. Suppose verdict: **inconsequential**. Record it. Stop.
5. Walk complete. Update 20260615090003 history. Surface table.
6. Total cascaded: 0 → no wide-cascade warning.

**Same scenario but 5 dependents all reference the cascade list**: cascade fires
on all 5, triggering the wide-cascade smell warning suggesting a `garden` run.
