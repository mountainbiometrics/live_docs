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

## Step 1 — Collect neighbors for each changed doc (fresh, every time)

For each changed doc id, retrieve its full neighbor set using:

```bash
python3 scripts/ld.py neighbors <id> --json
```

This returns `{depends_on, references, dependents, referenced_by}` — all
resolved to `{id, label, display}` entries. Use `depends_on` (upstream) and
`dependents` (downstream) for the cascade walk.

Do not read from `docs/.index/dependents.json` — always call `ld neighbors`
for fresh data. At this scale a full scan takes milliseconds and avoids
stale-cache errors.

If you need the full two-hop picture before starting, use:

```bash
python3 scripts/ld.py graph <id> --depth 2 --direction both --json
```

To surface dangling edges across the whole store before proceeding, run:

```bash
python3 scripts/ld.py edges --json
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
3. Collect neighbors via `ld neighbors <id> --json`; use `depends_on` entries
   (upstream) and `dependents` entries (downstream).
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

1. Load the doc to understand its current content:
   ```bash
   python3 scripts/ld.py show <n>
   ```
2. Make the minimum change needed to restore consistency. Use `ld set` for
   scalar frontmatter fields, `ld link`/`ld unlink` for edge changes, and
   direct file editing only for body-text changes that have no `ld` verb:
   ```bash
   # scalar field update
   python3 scripts/ld.py set <n> --status historical
   # edge update
   python3 scripts/ld.py link <n> --depends-on <new-dep-id>
   ```
   Do not refactor or rewrite beyond what the cascade requires.
3. Record the cascade history entry:
   ```bash
   python3 scripts/ld.py history <n> --add "cascade-check: updated because <source-id> changed — <one sentence why>"
   ```

## Step 6 — Update the originating doc's history

After the walk completes, record a history entry on EACH originally-changed doc
summarizing the cascade session outcome:

```bash
python3 scripts/ld.py history <changed-id> --add "cascade-check ran: <N> neighbors evaluated — <list each id: verdict>"
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

**Neighbors of 20260615090003** (from `ld neighbors 20260615090003 --json`):
`depends_on: []` (none upstream), `dependents: [{id: "20260615100010", ...}]`
(one downstream — a decision doc that lists 20260615090003 in its `depends_on`).

**Walk**:

1. Start: queue = [20260615090003]
2. Pop 20260615090003, mark visited. Call `ld neighbors 20260615090003 --json`.
   Upstream empty, one downstream: 20260615100010.
3. Evaluate 20260615100010 (downstream). Load it with `ld show 20260615100010`:
   - Read it. Its content references the decision type's cascade rules.
   - The change adds `goal` to the cascade list. Does 20260615100010 enumerate
     cascade targets? If yes — the list is now stale → **cascade**.
   - If no, it just cites the doc as context → **inconsequential**.
4. Suppose verdict: **inconsequential**. Record it. Stop.
5. Walk complete. Record history: `ld history 20260615090003 --add "cascade-check ran: 1 neighbor evaluated — 20260615100010: inconsequential"`. Surface table.
6. Total cascaded: 0 → no wide-cascade warning.

**Same scenario but 5 dependents all reference the cascade list**: cascade fires
on all 5, triggering the wide-cascade smell warning suggesting a `garden` run.
