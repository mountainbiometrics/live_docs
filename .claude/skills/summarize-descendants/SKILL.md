---
name: summarize-descendants
description: >
  Given a descendant-bearing doc (any doc that is the target of `belongs_to`
  edges) and the docs that `belongs_to` it, write that doc's
  BODY as an orientation guide to the grouping — a synthesis of what the members
  are, how each contributes to the grouping, and how they interrelate — the thing
  a reader reads to get oriented before diving into any member. There is no length
  limit on this body; it is the bulk of a signpost doc. Separately, set the doc's
  frontmatter `summary` to a tight 1–3 sentence signpost ("groups X; read here for
  X") — the same summary convention as any doc, NOT the guide in miniature.
  Synthesize, do not concatenate. Cascade-sensitive: the guide goes stale when a
  member changes, so re-run it on the parent whenever a member is
  substantively edited (cascade-check flags this). Use after curate-grouping wires
  memberships, or to refresh a stale signpost doc.
---

# summarize-descendants — Write a descendant-bearing doc's orientation guide

This skill applies to **any descendant-bearing doc** — any doc that is the target
of `belongs_to` edges, regardless of its `type`. Having descendants is what makes
a doc a navigational signpost; the role is structural, not a special type. A
signpost doc has two distinct outputs, and they are NOT the same thing:

1. **The body — an orientation guide (the main work, no length limit).** A
   synthesis of the grouping: what each member is, how it contributes to the
   grouping, how the members interrelate, where the weight and the tensions are.
   This is what a reader reads to get oriented *before* diving into any member —
   the bulk of a signpost doc's body.
2. **The frontmatter `summary` — a tight 1–3 sentence signpost.** Exactly like
   every other doc's summary: "this is the signpost for <macro-concept>; read here
   if you want <X>." It points at the grouping; it is not the guide condensed.

The cardinal rule for the body: **synthesize, do not concatenate.** Write the
account a human editor writes after reading every member — not a stack of the
members' own summaries glued together. The payoff is cognitive-load reduction
(see `20260615100004`, Cognitive Load Management): a reader gets oriented by
scanning the parent instead of absorbing every doc in the branch.

---

## Inputs

- **The descendant-bearing doc id** — any doc that is the target of `belongs_to`
  edges (it has members). Its `type` is irrelevant — a component, requirement,
  principle, decision, or any type can be a signpost by virtue of having
  descendants. There is no type guard; if the doc genuinely has no members there
  is nothing to summarize, but the role is read off topology, not off a type value.
- **Invocation context** — **standalone** (user ran it directly) or **nested**
  (called from `curate-grouping` or another orchestrator). Default: standalone.

## Step 0 — Capture start time (standalone only)

```bash
date -u +%Y-%m-%dT%H:%M:%SZ
```

Record the literal timestamp it prints (e.g. `2026-06-19T23:48:00Z`); you'll paste this exact value into `review new --since` at the end of the episode.

Skip entirely for nested invocations — the outer skill owns the timestamp and
the single review summary.

---

## Step 1 — Gather the parent and its members

Load the descendant-bearing doc and the docs that belong to it:

```bash
python3 scripts/ldoc.py show <parent-id>
python3 scripts/ldoc.py neighbors <parent-id> --kind dependents --json
```

The members are the docs that hard-edge *up into* this parent via `belongs_to` —
they appear as `dependents` of the parent. (`hierarchy.md` lists the same
children if you want a cross-check, but `neighbors` is the fresh source.)

For each member, read enough to characterize it — its `summary` is a starting
point, but read the body when the summary is thin or stale:

```bash
python3 scripts/ldoc.py show <member-id>
```

Skip `deprecated` members from the guide (they are no longer part of what the
grouping currently contains); if a deprecated doc is structurally still a member,
you may note it as superseded rather than describing it as live content.

---

## Step 2 — Write the body: the orientation guide (prose only)

The signpost doc's body is **only** the synthesized orientation guide —
LLM-authored prose, no length limit. It is your synthesis and your framing of the
grouping.

**Do NOT author or generate a `## Map`, a member list, or any structured
enumeration of members.** Membership lives in the `belongs_to` reverse-edge and
is rendered for the reader by consumers (the viewer renders the member list from
the edges); it is never duplicated in the body. There is no Map section. If a
prior run or `curate-grouping` left a `## Map` (or any member enumeration) in the
body, drop it — write the guide prose alone.

Write the orientation a reader needs:

- **What this grouping is** — the throughline that makes these docs one subject.
- **The members and how each contributes** — characterize each member in the
  context of the grouping (your framing, not a copy of its summary), and how it
  relates to the others: what builds on what, what tensions or trade-offs sit
  between them, where the weight is, what's missing. You are encouraged to
  reference specific members inline and elaborate on their gist freely — refer to
  any member you discuss via a resolvable `[[<member-id>]]` wiki-link (never a
  typed-out title) so the link resolves to the live label. This is prose
  referencing members, NOT a structured list of them.
- **Where to start** — the natural entry points and a sensible reading order.

Skip `deprecated` members from the live guide (note them as superseded if
structurally still attached). The test: a reader of the body alone can predict
what each member holds and decide which to open.

Load the current body, then write the full new body (the guide prose only),
replacing whatever `curate-grouping` or a prior run left:

```bash
python3 scripts/ldoc.py show <parent-id>            # read current body
python3 scripts/ldoc.py set <parent-id> --body -    # then pipe the full new body on stdin
```

---

## Step 3 — Write the frontmatter `summary` (a tight signpost)

The parent's `summary` is just a signpost — 1–3 sentences (≤ ~50 words, often one
is enough) naming the macro-concept and telling a reader what they'll find if
they descend. It follows the **same summary convention as every doc**; it is NOT
the orientation guide condensed.

- Model: *"The foundational principles that anchor all our decisions and goals —
  read here to understand the bedrock the rest of the store builds on."*
- Name the grouping and its purpose; the contents live in the body guide.

```bash
python3 scripts/ldoc.py set <parent-id> --summary "<the tight signpost>"
```

---

## Step 5 — Record history

```bash
python3 scripts/ldoc.py history <parent-id> --add "summarize-descendants: synthesized aggregated overview over <N> members"
```

---

## Step 6 — Validate

```bash
python3 scripts/ldoc.py validate
```

Address any ERRORs before finishing.

---

## Cascade-sensitivity (read this — it is the point)

This guide is **derived from the members**, so it goes stale the moment a
member changes substantively. The staleness is real, not cosmetic: a parent
whose guide describes a member's old claim actively misleads a navigator.
(Membership itself never goes stale in the body — it isn't stored there; the
viewer renders the member list live from `belongs_to`.)

- **Re-run this skill on the parent whenever any member is substantively
  edited** (title, body, type, status, or its membership changes). The guide
  prose must be regenerated to track the new member state.
- `cascade-check` enforces this automatically: when a doc that `belongs_to` a
  descendant-bearing parent (any `belongs_to` parent) changes, cascade-check
  emits a `cascade` verdict on the parent with the recommended fix "re-run
  `summarize-descendants` on the parent" (see cascade-check's
  descendant-summary rule). The fix for that cascade verdict is to invoke this
  skill, not to hand-patch the body.
- Membership changes from `curate-grouping` (a new member, a moved member) are
  likewise substantive — re-run this skill on every parent whose membership
  changed.

This is why the work belongs in a skill, not a one-time write: the overview is a
living derived artifact that must be refreshed, exactly like the cognitive-load
decision (`20260615204138`) intends.

---

## Review summary (standalone invocations only; FINAL step)

For **standalone** invocations, after the write completes:

```bash
python3 scripts/ldoc.py review new --since "2026-06-19T23:48:00Z"   # ← the literal value you recorded at the start
```

After it runs, confirm `touched` is non-empty and reflects the episode's changes.

Report the review id. Skip this step entirely for **nested** invocations — the
outer skill (`curate-grouping` or another orchestrator) owns the single review
summary for the episode. Review is **post-hoc and non-gating** (see
`review-is-post-hoc`).
