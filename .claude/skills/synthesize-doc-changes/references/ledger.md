# Ledger — synthesize-doc-changes

Edit history for skill refinements. Newest first.

## 2026-08-24 (third iteration) — Argument stance, not shape (Class A, continued)

**Failure:** After the shape-level fix (below), the batch still read as
pompous. The user supplied the diagnosis by writing a usable summary
themselves ("an LLM drafts the expectations for a given case, that is an
initial baseline, and human refinement on top of that baseline gives an
evolving target"): the docs were written as *arguments* — justifications of a
conclusion, conducted between abstractions, actors and mechanism missing —
where documentation should *describe* who does what and what it is for.
Summaries compacted every claim into fewer clauses and called it
distillation; real distillation is selection. The argument register also
concealed a factual error in 20260824202006 ("correction is the only point
where privileged knowledge enters") through synthesis, two style passes, and
two close readings — refinement actually stays inside the premise.

**Class:** A still — the missing information was the stance: describe, don't
argue.

**Diff:** Plain-register section rewritten wholesale: describe-don't-argue
leads (first sentence says what happens, named actors; why follows in the
body; summaries select rather than compact; given→new sentence construction;
plain nouns for actors, no role-jargon or epistemic vocabulary in place of
mechanism; repeat-back acceptance test; note that argument register hides
content errors). Round-two shape rules demoted to secondary mechanics.
Worked example replaced with the same summary in argument / polished-argument
/ description form — the middle one showing that a style pass without the
stance produces polished pomposity.

**Test:** uncoached executors re-run over the failing batch on skill text
alone, with content-contradiction flagging expected now that plain
description makes claims checkable.

**Amended same day (user-flagged over-anchoring):** the section as first
written narrated this store's failure history into the shared artifact —
"every register failure this store has recorded," a three-quote
store-specific worked example with the content-error anecdote, and a hard
"at most one contrast per doc" count. doc-style.md is shared across stores;
authoring-process material belongs here in the ledger, not the skill text.
Generalized: history narration removed, example cut to one compact
illustrative pair, the count softened to "a contrast earns its place only
when it is the decision itself." The rules themselves are unchanged.

---

## 2026-08-24 (second iteration) — Plain register is form, not diction (Class A, continued)

**Failure:** The first Plain-register fix (below) under-scoped the failure as
lexical — metaphor and synonym rotation. A rewrite pass under those rules
removed the flagged words and left the docs manifesto-shaped: concept-as-
subject epigrams, antithesis cadence ("X, not Y" throughout), closing
punchlines, thesis titles, slogan labels, maxim headings. A sentence can pass
the literal-reading test and still be a maxim. User supplied the diagnostic
("oracular: every decision dressed as an axiom") and the target register (the
across-a-desk engineer sentence).

**Class:** A still — the missing information was the *unit* of the rule:
sentence/document shape, not word choice.

**Diff:** Rewrote doc-style.md "Plain register" around shapes-to-refuse, each
with a mechanical tell (epigram → pull-quote test; antithesis → at most one
contrast per doc, where the contrast is the content; punchline → final
sentence must carry a fact; thesis titles/maxim headings → topic nouns and
working titles), shapes-to-write-in anchored to the store's older dry docs
(lists, tables, SVO sentences, named actors), and the real before/after
worked example (small-cases doc, manifesto vs working register). Kept v1's
metaphor, one-name-per-concept, established-term carve-out, and density
rules. label-title-summary.md: slogan/imperative labels named as
answer-shaped (with observed examples), and titles bound to working-title
register.

**Test protocol (new):** executors are given ONLY the skill files — no
failure examples or coaching in the prompt, which contaminated the v1 test —
and their rewrite of the failing batch is compared against the target
register. The skill text must carry the register on its own.

**Regression answers:** unchanged from the first-iteration entry — the edit
tightens prose form only; all 11 content/metadata properties untouched, the
naming properties (4, 8) further reinforced by the slogan-label rule.

---

## 2026-08-24 — Plain register (Class A, pattern-confirmed)

**Failure:** Doc prose — summaries worst — written in a figurative, aphoristic
register ("gold that guesses permanently mislays the finish line", "where
calibration gets its sharpest instruments"). User: it's technical
documentation, not storytelling; use existing terms; no synonym rotation.
Pattern: the 2026-08-21 sinai batch needed a full manual rewrite pass
("oracular"), then the 2026-08-24 batch reproduced the register.

**Class:** A — no skill text addressed prose register at all; doc-style.md
covered content discipline only. Pattern (two consecutive batches) justifies a
shared-file section. By the register test this is an invariant: figurative vs.
literal diction differing between executors is itself the bug.

**Diff:** New "Plain register" section in `_shared/doc-style.md` (one name per
concept; no new metaphor with a literal-reading test; aphorism ≠ compression;
density stays — with a carve-out keeping established metaphor-origin terms like
cascade/signpost/blast radius). Register line added to
`_shared/label-title-summary.md`. Pointer lines added where writers didn't
already read doc-style: revise-doc, garden-summarize, garden-refine (sampled
defect class), ingest-reference (normalized body), cascade-check (rewritten
text), and this skill's summary convention.

**Regression answers (all 11 properties):** 1 coherent-state, 2 provenance
edge, 3 incidental-for-ungrounded, 5 belongs_to≠requires, 7 incidental
reachable, 10 owned-claims-linked, 11 status-living — untouched (register is
diction, not content or metadata). 4 labels-name-subject, 6 claim-and-why,
8 source-vocabulary, 9 panelists naming/shape anchor — reinforced: the
one-name rule generalizes source-vocabulary from handles to prose. The
carve-out for established terms prevents the one foreseeable over-read
(stripping store vocabulary as "metaphor").

---

## 2026-08-04 — status:living default; deferral test for target (Class B)

**Failure:** Body-content rule "implementation lags → `status: target`" made
the write pass stamp current-work docs `target` whenever callers were
pre-implement (apply-to-docs).

**Class:** B — quoted rule permitted the bad reading. Shared definition
owns the fix (`_shared/status-living-vs-target.md`).

**Diff:** Step 3 status pointer + body-content rewrite to shared file;
default `living`; `target` only under shared deferral test.

**Regression answers:**
1. Coherent state not patches — yes; unchanged.
2. Provenance edge — yes; unchanged.
3. Incidental for ungrounded — yes; unchanged.
4. Labels name subject — yes; unchanged.
5. belongs_to ≠ requires — yes; unchanged.
6. Body states claim and why — yes; gap via status only when deferral test passes.
7–10. Incidental reachable / source vocabulary / panelists / owned claims — yes.

---

## 2026-07-28 — Owned claims linked, not restated (Class B)

**Failure:** Removing one catalog member (coverage audit) cascaded body/summary
rewrites across dependents that each restated the full capability enumeration.
Ideal change shape was edit the owning catalog (+ edges), not sync prose lists.

**Class:** B — "coherent state, not minimal patches" plus cascade list-sync
examples supported rewriting every shadow copy. Singular ownership existed in
the KB but write skills did not operationalize "link the owner."

**Diff:** Body-content rule applies `_shared/doc-style.md` for writing
discipline. Paired with cascade-check's collapse-not-sync repair and the
owned-claims section added to doc-style.

**Declined:** Promoting "every catalog member must be its own component" (hard
atomicity) — soft ownership (one catalog owner; dependents link) is enough for
this failure class.

**Regression answers:**
1. Coherent state not patches — yes; coherence means link-to-owner when the
   stale bit is a restated owned claim, not a synchronized copy.
2. Provenance edge — unchanged.
3. Incidental for ungrounded — unchanged.
4. Labels name subject — unchanged.
5. belongs_to ≠ requires — unchanged.
6. Body states claim and why — yes; plus must not restate another doc's owned set.
7–9. Incidental reachable / source vocabulary / panelists anchor — unchanged.

## 2026-07-23 — Level authority + vocabulary + attribution honesty (Class B + A)

**Failure:** (1) Unconfirmed agent articulations stamped as strong authority /
`requirement`; future agents treated them as user law. Root cause in skill text:
level rule treated missing provenance edge as the incidental trigger, but every
new doc already gets `--provenance <anchor>`, so incidental was unreachable.
(2) Agent-coined labels canonized over session vocabulary. (3) False speaker
attribution in bodies (consumer stores); blanket identical stamps.

**Class:** B for the dead incidental rule; A for vocabulary + attribution
honesty considerations.

**Diff:** Rewrote level classification: level = claim authority/settledness;
provenance edge ≠ raised level; default incidental without explicit user
utterance/confirmation of *this* claim; silence ≠ ratification; disambiguate
`level: requirement` from `type: requirement`. Added vocabulary preference,
attribution honesty (without forbidding consumer body conventions or future
tiers), and thin-decision→requires-root wiring.

**Declined:** Inventing a portable provenance-tier enum in this pass (user may
want tiers later; consumer free-form body conventions must remain allowed).

**Regression answers:**
1. Coherent state not patches — unchanged.
2. Provenance edge still required on new docs — yes; body tiers neither required
   nor forbidden.
3. Incidental for ungrounded — yes, and now actually reachable.
4. Labels name subject — yes; plus source-vocabulary preference.
5. belongs_to ≠ requires — unchanged; thin decisions also require roots.
6. Body states claim and why — unchanged; false speaker attribution restricted.
