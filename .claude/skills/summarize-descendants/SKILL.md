---
name: summarize-descendants
description: >
  Given a `type: index` doc and the docs that `belongs_to` it, SYNTHESIZE an
  aggregated overview of the grouping — a coherent narrative of what the subtree
  is and what's in it — and write it to the index doc's `summary` field and a
  body `## Map` section (one line per member: label — one-clause gist). This is
  synthesis, not concatenation of child summaries: a reader should grasp the
  shape of the whole subtree without opening each child. Cascade-sensitive: the
  overview goes stale when any member changes, so re-run it on the parent index
  whenever a member is substantively edited (cascade-check flags this). Use after
  curate-grouping wires memberships, or to refresh a stale index summary.
---

# summarize-descendants — Synthesize an index's aggregated overview

The cardinal rule: **synthesize, do not concatenate.** The output is a coherent
account of *what this grouping is and what it contains* — the kind of overview a
human editor writes after reading every member, not a stack of the members' own
summaries glued together. A reader should be able to understand the shape of the
subtree from the index alone, which is the cognitive-load payoff (see
`20260615100004`, Cognitive Load Management): navigate by scanning, not by
absorbing every doc in the branch.

This skill writes only to the index doc itself — its `summary` scalar and a
body `## Map` section. It does not touch the members.

---

## Inputs

- **The index doc id** — a `type: index` doc. If the ref given is not
  `type: index`, stop and say so (this skill only summarizes index/MOC docs).
- **Invocation context** — **standalone** (user ran it directly) or **nested**
  (called from `curate-grouping` or another orchestrator). Default: standalone.

## Step 0 — Capture start time (standalone only)

```bash
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
```

Skip entirely for nested invocations — the outer skill owns the timestamp and
the single review summary.

---

## Step 1 — Gather the index and its members

Load the index doc and the docs that belong to it:

```bash
python3 scripts/ldoc.py show <index-id>
python3 scripts/ldoc.py neighbors <index-id> --kind dependents --json
```

The members are the docs that hard-edge *up into* this index via `belongs_to` —
they appear as `dependents` of the index. (`hierarchy.md` lists the same
children if you want a cross-check, but `neighbors` is the fresh source.)

For each member, read enough to characterize it — its `summary` is a starting
point, but read the body when the summary is thin or stale:

```bash
python3 scripts/ldoc.py show <member-id>
```

Skip `deprecated` members from the active Map (they are no longer part of what
the grouping currently contains); if a deprecated doc is structurally still a
member, you may note it as superseded rather than listing it as live content.

---

## Step 2 — Synthesize the aggregated overview

This is the judgment step. Having read all members, write a coherent narrative —
**not** a list of their summaries:

- **What the grouping is** — the throughline that makes these docs one subject.
  What question does a reader come here to answer?
- **What's in it** — the shape of the subtree: the main sub-themes, how the
  members relate, where the weight is, any notable tension or gap.
- **Where to go next** — if some members are the natural entry points, say so.

Synthesis means: collapse overlap, surface the connective tissue the individual
docs don't state about each other, and describe the whole at a higher altitude
than any single member. If two members make the same point from different
angles, say that once. The test: someone who reads only this overview should be
able to predict what they'll find inside, and decide which member to open — that
is impossible from concatenated child summaries.

Keep it to a few sentences (the `summary` field is a 2–5 sentence overview).

---

## Step 3 — Write the summary scalar

```bash
python3 scripts/ldoc.py set <index-id> --summary "<the synthesized overview from Step 2>"
```

---

## Step 4 — Write the `## Map` section in the body

The Map is the navigational directory: one line per live member, in a sensible
reading order (entry points first, or grouped by sub-theme), each as
`label — one-clause gist`. The gist is *your* one-clause characterization of the
member in the context of this grouping, not a copy of its summary.

Load the current body, preserve everything except a prior `## Map` section
(replace it if present), and write the new body:

```bash
python3 scripts/ldoc.py show <index-id>            # read current body
python3 scripts/ldoc.py set <index-id> --body -    # then pipe the full new body on stdin
```

The `## Map` section shape:

```
## Map

- [<Label>](<member-id>.md) — <one-clause gist of this member in context>
- [<Label>](<member-id>.md) — <one-clause gist>
- …
```

Keep the index doc's existing intro prose (the "what this grouping is"
statement) above the Map; replace only the Map section. The Map mirrors current
membership exactly — add new members, drop members no longer belonging.

---

## Step 5 — Record history

```bash
python3 scripts/ldoc.py history <index-id> --add "summarize-descendants: synthesized aggregated overview over <N> members"
```

---

## Step 6 — Validate

```bash
python3 scripts/ldoc.py validate
```

Address any ERRORs before finishing.

---

## Cascade-sensitivity (read this — it is the point)

This overview is **derived from the members**, so it goes stale the moment a
member changes substantively. The staleness is real, not cosmetic: an index
whose Map describes a member's old claim actively misleads a navigator.

- **Re-run this skill on the parent index whenever any member is substantively
  edited** (title, body, type, status, or its membership changes). The aggregated
  summary and Map must be regenerated to track the new member state.
- `cascade-check` enforces this automatically: when a doc that `belongs_to` a
  `type: index` parent changes, cascade-check emits a `cascade` verdict on the
  parent index with the recommended fix "re-run `summarize-descendants` on the
  parent index" (see cascade-check's index-summary rule). The fix for that
  cascade verdict is to invoke this skill, not to hand-patch the Map.
- Membership changes from `curate-grouping` (a new member, a moved member) are
  likewise substantive — re-run this skill on every index whose membership
  changed.

This is why the work belongs in a skill, not a one-time write: the overview is a
living derived artifact that must be refreshed, exactly like the cognitive-load
decision (`20260615204138`) intends.

---

## Review summary (standalone invocations only; FINAL step)

For **standalone** invocations, after the write completes:

```bash
python3 scripts/ldoc.py review new --since "$START"
```

Report the review id. Skip this step entirely for **nested** invocations — the
outer skill (`curate-grouping` or another orchestrator) owns the single review
summary for the episode. Review is **post-hoc and non-gating** (see
`review-is-post-hoc`).
