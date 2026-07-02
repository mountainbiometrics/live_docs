# Editing sessions — the lifecycle every change runs inside

Single source of truth for how an actor drives an editing session: how work is
opened, attributed, explained, and closed into one review. Read and apply this;
do not restate the mechanics in each skill. The *why* lives in the KB (Editing
Session, On-Disk Session Records, Session Change Log, Change-Type Taxonomy,
Sessions Are Required).

## The one rule

Every store **mutation** happens inside an **open session**. A session is the
actualized "episode": one owner opens it, every change during it is attributed
to it, and closing it mints exactly **one** review.

## Open — episode owner only

At the start of the episode, open a session and export it, so every later `ldoc`
call — and every subagent that inherits the environment — attributes to it:

```bash
export LDOC_SESSION=$(ldoc session start)
```

`ldoc session start` prints the id and **errors if `LDOC_SESSION` is already
set** (re-opening over a live session is almost always an accident). If a
mutation ever runs with no open session, `ldoc` auto-creates one and says so —
but the owner should open explicitly so the whole episode lands in one session.

## Mutate — everyone

Just make your edits. Attribution and classification are **ambient**:

- Every mutation is stamped with the open session automatically — **no timestamp
  to capture, nothing to thread through arguments.**
- Each change's **`change_type`** (addition / revision / restructure /
  organizational / deletion) is computed from the command — **you never classify
  by hand.**

**Explaining a change (`--note`):**

- **Obvious** structural ops auto-fill their note — `new`, re-parent, `unlink`,
  `rm`. Nothing to write.
- A **revision** — a change to `body`, `label`, `title`, or `summary` — needs an
  author note: pass `--note "<why>"` on the mutating command. Missing it only
  warns per-command, but **`session close` blocks** until every revision-touched
  doc carries one author note. One note per doc suffices.
- `ldoc history <id> --add "<note>"` still exists but is **deprecated** to a
  post-hoc gap-filler — reach for it only to satisfy a close-gate after the fact.

## Close — episode owner only

At episode end, close the session; this mints the single review over everything
the session touched (built from its change log, so deletions are included too):

```bash
ldoc session close --summary "<one-line agent recap of the episode>"
```

The `--summary` is the **agent's recap** — the commit-message / PR-title of the
episode, *not* a human sign-off. It is optional but recommended; you may also set
it earlier with `ldoc session summary <id> "..."`. Review remains post-hoc and
non-gating: closing never blocks a change, it only nudges for missing notes.

## Nested phases do NOT open or close

A phase sub-skill invoked by an owner (cascade-check, the garden-* phases, the
mapping/synthesis phases) **inherits** the ambient session and just mutates —
passing `--note` on revisions. It must not `session start`, `session close`, or
capture any timestamp. Episode ownership belongs to the top-level skill alone:
**one episode = one session = one review.**

## Recovering fragments

If work got split across several auto-created sessions (an agent forgot to
export), `ldoc session list` shows the open ones and `ldoc session merge
<ids...>` folds them into the earliest before close. `ldoc session resume <id>`
re-exports an id to keep working under it.
