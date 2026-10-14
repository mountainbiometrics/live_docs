# Ledger — synthesize-doc-changes

Edit history for skill refinements. Newest first.

## 2026-10-14 — Mechanism narrated as doctrine (Class A)

**Failure:** An apply-to-docs batch wrote token-issuance choreography into a
principle (identity apart from proof), a constraint (carrier is the
transport's), and a component (the auth context), each from its own vantage:
"the transport then issues its own token" / "the proof context only issues
tokens" / "it issues and resolves user tokens … the transport then mints its
own token". No decision recorded who constructs a token. An audit reported
the drift as a contradiction and proposed a passing version that picked a
mechanism; the orchestrator then asked the owner to settle a second
mechanism question (which credential kinds MCP write tools accept) that no
doc's claim decided. Owner: the store catches conflicting design decisions
and does not dictate implementation; indicative mechanism sentences and
commanding prose are read downstream as doctrine, and the owner has to
re-explain this to every agent.

**Class:** A. cruft-verdicts' incidental-detail test and doc-types'
why-not-what covered stripping a dead or incidental name, but no text said
that a mechanism sentence in a claim body is read as a decision, that drift
between docs on an unowned mechanism is over-specification rather than a
conflict, or that body prose carries no modal force beyond the `force`
facet. conflict-test.md covers same-claim-at-which-intent and did not reach
"not a claim at all".

**Diff:** New `_shared/doc-style.md` section "Mechanism is not the claim":
mechanism belongs to the implementation (or `## Implementation`); the two
failure shapes (doctrine downstream, false conflict across docs); unowned
disagreement is removed from each doc, never arbitrated or asked; the
survival test points at cruft-verdicts; `force` is the only binding
strength. audit-docs gained the matching checks and the rule that such a
disagreement never becomes a Consideration (its own ledger).

**Amended same day (owner-flagged under-correction):** the section as
first written kept a survival test ("mechanism stated inside claims that do
not need it"), which leaves the decision to the writer. Owner: not "if the
claim does not need it" but ever; the only doc that names a mechanism is a
decision whose claim is that mechanism, chosen and not merely built, and
nothing outside a doc's own claim is stated as fact, because that reaches
outside its responsibility. By the register test this is an invariant (two
writers differing on whether a mechanism sentence stays is the bug).
Rewritten: the rule leads, the responsibility boundary generalizes it to
any fact outside the claim, the why follows. cruft-verdicts' subject test
now asks whether the doc is the decision for the name, not whether the
sentence survives without it.

**Tested (blind, same day):** a Sonnet executor given only the revise-doc
skill path and the three doc ids, with doc-style read in full (verified in
its transcript). Caught: the deferral wording in all three, the principle's
"transport then issues its own token", the constraint's per-transport
carrier list. Missed: it resolved the disagreement by keeping "the proof
context issues tokens" in the component and the constraint (the constraint's
title names that mechanism, so it treated the constraint as the owner under
the owned-claims rule and removed the other side); the component still
states "issues and resolves user tokens", "calls the accounts context, never
the reverse", and "writes … to the audit context". Diagnosis: the executor
removed the sentence the section quotes as an example and little else; a
non-decision doc's title naming a mechanism read as ownership; nothing said
what a component's claim is as against its mechanism. Amended: descriptors
are under the rule and confer no ownership; a component's claim is its
responsibility and why, not what it issues, calls, or writes to; the rule
applies to every sentence, not to those resembling the examples.

**Re-tested after the amendment (same executor tier, same brief):** the
component now states its responsibility and its why, with the dependency
direction, what it writes to, and "issues and resolves" gone; the principle
is clean; the constraint keeps "the proof context issues tokens and checks a
presented token" in body and summary. The inter-doc disagreement is gone, but
one non-decision doc still names the mechanism. Left as is for the owner to
weigh: a third tightening aimed at that phrase would be correcting toward the
last failure.

**Declined:** editing conflict-test.md (its subject is same-claim intent
comparison; the new section says when there is no claim to compare) and
cruft-verdicts.md (the incidental-detail test already serves as the
survival test; the register point belongs in doc-style).

**Regression answers:** 6 body states claim and why — reinforced (the why
survives; mechanism does not). 12 plain register — consistent: describing
who does what applies to the claim, not to the code. Detail that is a doc's
subject (a contract's field names) still survives the incidental-detail
test. Others unchanged.


## 2026-10-14 — Contradicted sentence: implementation wording or intent (Class A)

**Failure:** see apply-to-docs ledger, same date. The revision raised a
requirement's intent from the owner's words yet left a sentence in it about
how much slack a check leaves, which those words opposed, because the
executor could not tell whether the owner's phrase referred to it; the
orchestrator then asked the owner about the sentence.

**Class:** A. Step 2 and the cardinal rule say not to leave contradictions
coexisting, but give no test for a sentence whose contradiction is uncertain,
and no distinction between implementation wording (not the store's to own)
and a statement of intent (check for its reason).

**Diff:** Step 2 gains a judgment block: implementation wording the claim does
not need (cruft-verdicts incidental-detail test) is stripped, not moved to
`## Implementation`, and doubt about the person's referent is no reason to
keep it; a statement of intent is checked for its reason — none, or already
answered, means stale and rewritten; an unconsidered reason is handed to the
caller as the consideration itself. Output template gains an optional
"Unconsidered reasons" block.

**Declined:** changing cruft-verdicts' "current implementation detail has a
place" (still right for detail the change does not override); changing the
verdict-driven write behavior for a found reason (the write still follows the
verdict; raising is the orchestrator's call).

**Regression answers:** 1 coherent state — reinforced. 2–5, 7–11 — unchanged.
6 body states claim and why — reinforced. 12 plain register — unchanged.
Detail that is a doc's subject (a contract's field names) still survives the
incidental-detail test.


## 2026-10-14 — Clarification shortens a doc (Class B, with an A consideration)

**Failure:** A 2026-10-13 run folding a settled design into four existing docs
grew each one. A signpost already past its paragraph ceiling gained a context
paragraph linking four new docs; a decision's shared-mechanics list was
extended by one more item; an example paragraph was removed only because it
described superseded behavior. Owner: docs should get simpler as their subject
gets clearer; agents "add on" where they should "revise, clarify, and clean up."

**Class:** B. Every rewrite trigger on the write path keyed on falseness and
scoped the rewrite narrowly: Step 2 "Rewrite the affected portion ... If the
prior text would now be misleading"; revise-doc Step 3 "Make the minimum
change" and "no refactoring beyond scope"; doc-style "every sentence that
became false is removed." True-but-redundant, hedged, or historical text had
no license to go, so new material could only be appended. The A part: no text
said a clearer subject usually means a shorter doc.

**Diff:** New `_shared/doc-style.md` section "Clarification shortens a doc"
(judgment: whole-body reread, redundant/hedged/historical as cut reasons,
examples/lists/context earn their place, past-ceiling bodies come out shorter
or split, signposts rewrite orientation instead of a paragraph per arrival,
selection not compaction; survives: the why, rejected-alternative contrast,
subject detail, history entries, edges, Correction, Implementation section).
One invariant: a revision whose body grew says why in its `--note`
(verifiable; the owner's own "growth needs a reason"). This skill: cardinal
rule gains one sentence; Step 2 reads the whole body and points at the shared
section. revise-doc Step 3 disambiguated (see its ledger).

**Declined:** a word or percentage limit (owner asked for judgment); edits to
cascade-check (its "minimum change that restores consistency" scopes neighbor
churn, and it already applies doc-style to rewritten text); garden-cruft
(gardening repairs after the fact; the failure is at write time); revise-doc's
substantive/provenance classification (it decides cascade and history, not
prose).

**Regression answers:** 1 coherent state — reinforced. 2 provenance edge, 3/7
incidental, 4/8 labels and vocabulary, 5 belongs_to vs requires, 11 status
living — untouched. 6 claim and why — kept explicitly in "what survives." 10
owned claims — reinforced (list growth prompts a link to the owner). 12 plain
register — consistent: shortening is selection, compaction is named as the
wrong form. No ping-pong: no earlier entry argued for keeping redundant text.

---

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
Pattern: a 2026-08-21 consumer-store batch needed a full manual rewrite pass
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
8 source-vocabulary, 9 consumer-store QA naming/shape anchor — reinforced: the
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
7–10. Incidental reachable / source vocabulary / consumer-store QA anchor / owned claims — yes.

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
7–9. Incidental reachable / source vocabulary / consumer-store QA anchor — unchanged.

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
