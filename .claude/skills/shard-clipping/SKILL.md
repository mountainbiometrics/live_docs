---
name: shard-clipping
description: >
  Gate 1.5 pre-pass between promote (gate 1) and ingest-reference (gate 2),
  normally invoked by ingest-reference as its first sub-step (it can also be run
  standalone). Estimates how many atomic concepts a promoted raw clipping would
  decompose into. VOLUME is the only trigger: if the clipping fits one ingest pass
  (a generous floor of ~50 atomic concepts — most clippings, including dense
  multi-subject design notes, pass through unchanged), it passes through. Only when
  the clipping carries far more concepts than one pass can synthesize (a 10k-line
  mega-doc, a sprawling spec) does it shard — cutting along concept clusters into
  child raw clippings, each small enough to ingest in one pass, by gathering the
  VERBATIM passages per cluster (non-contiguous and overlapping allowed; full
  coverage is the one rule). Children are left PENDING for the backlog loop to
  ingest — each runs the whole ingest-reference pipeline on its own portion, so
  comprehension and synthesis stay fused per shard. Use when a raw clipping is so
  large it would stall the gate-2 ingest agent because one context cannot hold both
  the comprehension of the whole document and the synthesis of every atomic doc it
  decomposes into. Topical disjointness is NOT a trigger — it only guides where to
  cut once volume forces a split.
---

# shard-clipping — Divide the unit of work before gate 2 (orchestrator)

**Where this sits (the inbox pipeline, with gate 1.5):**

- **Gate 0 — capture:** `ldoc inbox add`. Instant, no processing.
- **Gate 1 — accept (promote):** `ldoc promote <id>` moves inbox → `raw/` with
  raw-clipping frontmatter.
- **Gate 1.5 — shard (this skill):** decide one gate-2 run or many. Runs on a raw
  clipping in `raw/`. Either passes the raw through unchanged, or cuts it into
  child raw clippings.
- **Gate 2 — ingest:** `ingest-reference` runs on each raw (the original, or each
  child shard). This is where atomicity is produced and MUST NOT be skipped.

**This skill is normally invoked by `ingest-reference`** as its first sub-step (a
nested invocation), so it is never an orphan you have to remember to run — every
ingest passes through the shard decision, which is a near-no-op for the common
small clipping. It may also be run standalone to pre-shard a known-large raw.

The cardinal rule: **divide the unit of work, not the phases.** We never split
`ingest-reference` into a plan-phase and an apply-phase — comprehension and
synthesis are fused. Instead we shrink the thing gate 2 operates on so one
context can hold both. **Shards are gatherings of verbatim passages, never
rephrasings** — so each gate-2 run keeps full nuance over its portion. (Rationale
and the rejected plan/apply split: `reports/shard-clipping-design.md` §2.)

This skill is a **thin orchestrator**. Its unique parts are the sharding verdict
and the verbatim child-raw cuts; the actual decomposition is entirely
`ingest-reference`'s job, invoked once per resulting raw.

---

## This skill OWNS its episode (recursion / duplicate-review discipline)

Same "orchestrator owns the episode" contract as `ingest-reference` and
`cascade-check`:

- **Standalone** (a human invokes shard-clipping directly to shard a raw):
  shard-clipping owns the episode — it opens the session (Step 0) and closes it
  into **one** review covering the child-raw creation (Step 6). The downstream
  gate-2 ingests are SEPARATE episodes with their own reviews — shard-clipping does
  NOT wrap them in one giant review.
- **Nested** (invoked by `ingest-reference`, the normal case): shard-clipping is a
  nested invocation that **inherits the ambient session** — it must NOT open a
  session (skip Step 0) and must NOT `session close`; only the outer
  `ingest-reference` owner opens the session and closes it into the review.
- shard-clipping does **not** ingest the children and does **not** own their
  reviews. Each child is ingested later, as its **own** independent gate-2 episode
  (driven by the pending-raw loop), owning its own single review — exactly like a
  normal ingest.

Net: a `shard` run owns **one** review (the child-raw creation, and only when
standalone). The N downstream ingests are separate, later episodes with their own
N reviews — not this skill's concern.

---

## Inputs

- **A raw clipping id** — a `raw/<id>.md` that has already been promoted (gate 1).
  If given an inbox item, stop and tell the caller to `ldoc promote` it first
  (gate 1 precedes gate 1.5). If given a `docs/` id, stop — this skill operates on
  the raw tier only.
- **Invocation context** — **nested** (default, when called by ingest-reference)
  or **standalone**.

---

## Step 0 — Open the editing session (standalone only)

```bash
export LDOC_SESSION=$(ldoc session start)
```

Read and apply `.claude/skills/_shared/session-lifecycle.md`. **Skip this step
entirely for nested invocations** — the nested shard inherits the outer skill's
ambient session, which owns opening and closing it.

---

## Step 1 — Load the raw clipping and its provenance

Read the raw clipping through the porcelain (the raw tier is outside the graph,
so `ldoc show`/`body` do not resolve raw ids — `raw show` is the read path):

```bash
ldoc raw show <RAW_ID>      # frontmatter + verbatim source text
```

Note the parent's provenance frontmatter — `origin`, `medium`, `authored_at`,
`captured`, `original_source` — and its `shard_depth` (0 if this is the
originally-promoted raw). You do not need to copy these by hand: `ldoc ingest-raw
--inherit-from` (Step 5b) carries them to each child automatically.

> **Truncated bodies.** If the raw body was truncated at ingest (the
> `ingest-reference` Step 2 ">~2000 words" note), it is NOT a faithful verbatim
> original — do NOT slice it. Shard from the full source artifact named in
> `original_source` instead (read it with `--from-file`).

---

## Step 2 — Sharding verdict: is the CONCEPT VOLUME too large for one pass? (THE DECISION)

**Volume is the only trigger.** The single question is whether this clipping
carries *so many atomic concepts* that one agent could not comprehend AND
synthesize all of them in one fused gate-2 pass. Topical unity is irrelevant to
*whether* to shard — a clipping entirely about one subject still shards if it is
big enough; a clipping spanning five unrelated subjects still passes through if it
is small. (Disjointness matters only in Step 3, for deciding *where* to cut.)

**Estimate concept volume, NOT word count.** Length is a poor proxy — a dense
one-page table and a rambling ten-page status update can carry opposite concept
counts. Estimate **how many atomic docs a full gate-2 ingest would decompose this
into** (survey the structure; you do not need to enumerate them precisely).

**The floor is generous — bias hard toward pass-through.** A capable agent
comfortably holds a few dozen atomic concepts in one pass. Only shard when the
estimate is **well above ~50 atomic docs**. Concretely:

- **≤ ~50 atomic docs → `pass-through`.** One gate-2 run holds it. This is the
  overwhelming common case. *Example: this repo's `idea_dump.md` decomposes into
  ~35 atomic docs across many subjects (doc model, graph model, lifecycle,
  principles, prior art) — and still passes through, because one agent reads it,
  reasons about it, and decomposes it without strain.* Many concepts under many
  subjects is normal gate-2 work, not a reason to shard.
- **\> ~50 atomic docs → `shard`.** The clipping would overflow one synthesis pass
  (a 10k-line mega-doc, a sprawling multi-part spec). Go to Step 3 to cut it into
  a handful of smaller units, each itself comfortably under the floor.

The ~50 figure is a deliberately conservative rule of thumb, not a hard gate — if
you genuinely cannot tell, prefer `pass-through` and let gate 2 do its job.

| Verdict | Meaning | Next |
|---------|---------|------|
| `pass-through` | ≤ ~50 atomic docs; one gate-2 run holds it. | Go to Step 5a. |
| `shard` | \> ~50 atomic docs; overflows one pass. | Go to Step 3. |

---

## Step 3 — Cut into coarse shards along concept clusters

Only on a `shard` verdict. **This is where disjointness finally matters** — not
for *whether* to shard (Step 2 already decided that on volume) but for *where* to
cut. Group the material into its natural over-arching concept clusters and make
each cluster a shard.

**Sizing target: as few shards as possible, each comfortably under the ~50-concept
floor** so that every shard is itself a clean single-pass `pass-through` unit. Do
not over-split — "split it up a little bit," not one-shard-per-concept. As a rough
guide, aim for roughly ⌈estimated concepts ÷ ~30⌉ shards (≈100 concepts → 3–4
shards; a 10k-line mega-doc → as many as it takes to get each shard under the
floor), cutting at the document's own cluster boundaries.

A shard is **not** a contiguous cut at a single seam — it is a *gathering* of the
source passages that belong to one cluster, pulled from wherever they sit. One
shard might be "paragraph 1 + paragraphs 5–10 + section 4 + section 12"; the next
"paragraphs 1–6 + sections 8–12". That is fine. You do not need clean seams (a
wall-of-text source with no headings is fine too) — you select which passages go
together.

Rules:

- **Verbatim passages, no rephrasing.** Every passage you place in a shard is exact
  source text. You are *selecting and grouping*, never paraphrasing or summarizing
  in your own words. (It is "summarizing" only in the sense of decomposing — which
  passages belong together — the words stay the source's.)
- **Non-contiguous and overlapping are both fine.** Passages need not be adjacent,
  and the same passage (a shared preamble, a definitions block, a framing sentence)
  may appear in more than one shard when more than one cluster needs it.
- **Full coverage is the one hard rule.** Every piece of the source text must land
  in at least one shard. Overlap is allowed; *omission is not*. Verify coverage
  before creating children.
- **Each shard must come in under the floor.** If a cluster is *itself* still
  > ~50 concepts, it will shard again at its own Step 2 (bounded by the depth cap,
  Step 4) — that is expected, not a problem.

The **parent raw is the immutable whole-archive** — never edit it, never delete
it, never shard it in place. Sharding only *adds* child raws alongside it.

---

## Step 4 — Termination / recursion floor (before creating children)

A child may itself still be over the volume floor and shard again — but recursion
must terminate. Apply all three stops:

1. **Under-the-floor halts (base case).** A shard estimated at ≤ ~50 atomic docs
   gets `pass-through` at its own Step 2 and goes straight to gate 2. This is the
   normal terminator, and the goal of the Step 3 sizing target.
2. **No-progress guard.** If a still-too-large clipping cannot be cut into ≥2
   smaller shards — e.g. it is one genuinely indivisible high-volume concept, so
   every split leaves one piece essentially the whole — STOP and pass it through
   to gate 2 as-is rather than tearing a single concept across shards. (Rare; most
   high-volume material has cluster boundaries to cut on.)
3. **Depth cap = 2 levels** (parent → children → grandchildren). At the cap, force
   `pass-through` regardless of estimated volume — gate 2's own decomposition
   handles whatever concept count remains within a shard.

Depth is recorded durably on each child: `ldoc ingest-raw --inherit-from`
auto-sets `shard_depth = parent.shard_depth + 1`, so the cap survives across
separate episodes. (Read it back with `ldoc raw show <id>`.)

---

## Step 5 — Create child raw clippings (or pass the original through)

### 5a — pass-through

Nothing to create. The single original `raw/<RAW_ID>.md` is the unit for gate 2.
Skip to Step 6 with the unit list `[RAW_ID]`.

### 5b — shard: create one child raw per cluster

For each concept cluster's gathered passages from Step 3, create a child raw
clipping with the porcelain. `--inherit-from` copies the parent's `origin` /
`medium` / `authored_at` / `captured` / `original_source`, sets `parent_raw`, and
auto-derives `shard_depth`:

```bash
ldoc ingest-raw \
  --body -                       \  # the gathered verbatim passages on stdin
  --title "Shard N/<total>: <cluster title> (of <parent title>)" \
  --inherit-from "raw/<PARENT_RAW_ID>.md"
```

Note each created child id: call it **CHILD_RAW_ID**.

**Why a `parent_raw` pointer and not a `requires` edge:** raw files are not graph
nodes (AGENTS.md edge rules). A `requires` pointing at a raw id would be a
dangling edge. `parent_raw` is a raw-tier-to-raw-tier provenance pointer (a path,
exactly like a normalized doc's `source: "raw/<id>.md"`), living entirely outside
the graph — `validate`/`reindex` never resolve it.

If a child is itself still `shard` at its own Step 2 (and the floor permits),
recurse: run this skill's Steps 2–5 on that child (its `--inherit-from` will set
`shard_depth` to 2, hitting the cap).

### 5c — the children are now pending

After 5b you have created `[CHILD_RAW_ID_1, CHILD_RAW_ID_2, ...]`. The parent raw
is the archive — it is NOT a gate-2 unit once sharded. You can enumerate the
children any time with `ldoc raw children <PARENT_RAW_ID>`, but **do not read their
bodies** — that would re-accumulate the bulk you just shed.

---

## Step 6 — Leave the shards pending (do NOT ingest them here)

The child raws you just created are ordinary **pending** raw clippings (no
`ingested_at`, not yet referenced by any doc). **Do not ingest them from this
skill, and do not read their contents.** Driving gate 2 here would pull every
shard's text back into one context — the very thing sharding exists to avoid.

They are picked up downstream by whatever iterates pending raws — the backlog loop
over `ldoc raw list --pending`, or a later `ingest-reference` invocation. Each
shard is then its own independent gate-2 episode. **Order does not matter:** if two
shards share a concept, the duplicate is reconciled by `map-concepts-to-docs`'
concept-matching and the gardening passes. Duplicates across docs are expected and
handled — they are NOT a reason to serialize the ingests.

Once every child has been ingested, `ldoc raw list` derives the parent as
`[sharded]` automatically; while any child is still pending it shows `[sharding]`
and the pending children appear in `raw list --pending`.

---

## Step 7 — Report and review summary (FINAL step)

Print a summary:

```
shard-clipping — complete
Parent raw: raw/<RAW_ID>.md   "<parent title>"   (immutable whole-archive)
Verdict: <pass-through | shard (N children)>   depth: <d>

Children created (shard only) — left PENDING for the backlog loop:
  raw/<id>.md  "Shard 1/N: <cluster title>"   parent_raw -> raw/<RAW_ID>.md
  raw/<id>.md  "Shard 2/N: <cluster title>"   parent_raw -> raw/<RAW_ID>.md

(Not ingested here. They surface in `ldoc raw list --pending`; each becomes its
own gate-2 episode when the pending-raw iterator reaches it.)
```

**Close the session — standalone, AND only if children were created.** A
`pass-through` run creates no child raws and mutates nothing; by the garden
"change passes only" precedent it mints NO review (it merely hands the existing
raw to gate 2). A `shard` run created child raws, so closing the session mints one
review covering that creation:

```bash
ldoc session close --summary "<one-line agent recap of the episode>"
```

The review is built from the session's change log; confirm `touched` reflects the
new child raws. Report the id:

```
Review summary created: <id>   (reviews/<id>.md)
```

**Skip the close entirely for nested invocations** — the nested shard inherited
the outer `ingest-reference` session, which owns closing it. Review is post-hoc
and non-gating: it records the sharding act for later signoff and never blocks it.
The gate-2 ingests carry their own separate reviews.

---

## Checklist before finishing

- [ ] Verdict was made on **concept VOLUME** (estimated atomic-doc count vs the
      ~50 floor) — NOT word count, and NOT topical disjointness.
- [ ] Biased hard toward `pass-through`; sharded only when the estimate is well
      above ~50 atomic docs. (A dense, multi-subject but normal-size note passes
      through.)
- [ ] Every passage in every shard is **verbatim** source text — selected and
      grouped, never rephrased or summarized in your own words.
- [ ] **Full coverage**: every piece of the source lands in ≥1 shard (overlap and
      non-contiguous selection are fine; omission is not).
- [ ] Each child was created with `ldoc ingest-raw --inherit-from` (inherits
      `origin` / `medium` / `authored_at` / `captured` / `original_source`, sets
      `parent_raw`, auto-derives `shard_depth`).
- [ ] The parent raw is untouched — immutable whole-archive; never the direct
      gate-2 unit once sharded.
- [ ] Termination floor honored: under-the-floor halts, no-progress guard, depth
      cap = 2 (`shard_depth`).
- [ ] Children left **pending** — NOT ingested or read by this skill; the
      pending-raw loop drives gate 2 (order-independent; duplicates tolerated).
- [ ] Standalone `shard` run emitted exactly one sharding review; `pass-through`
      emitted none; nested invocation emitted none.
