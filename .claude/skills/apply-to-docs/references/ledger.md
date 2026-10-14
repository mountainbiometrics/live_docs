# Ledger — apply-to-docs

Edit history for skill refinements. Newest first.

## 2026-10-14 — Implementation wording escalated as a question (Class A)

**Failure:** A 2026-10-13 run recorded a settled design and ended its report
by asking the owner whether an unclear phrase of theirs referred to a sentence
in a requirement doc about how much slack a size check leaves, saying the
sentence "needs your call". The sentence was implementation wording inside a
requirement; the raw material already said the check should carry no such
slack, and the run had already raised that requirement's intent on those
words. Owner: the store catches conflicting intent and does not dictate
implementation; contradicted implementation wording is purged; an opposing
doc is checked for a reason, fluff is deleted, and only a reason the new
material did not consider is raised, as the consideration, never as "the
store says X".

**Class:** A. No text told the executor to judge what kind of statement a
contradicted sentence is, and nothing said what an owner-facing question must
contain. Step 5 governs pausing only, so the report was an unguarded channel:
uncertainty about the owner's referent became a question. Not B: no sentence
licensed the question; not a pause-gate failure as such.

**Diff:** Step 8 gains "What may go to the person" (judgment): a question or
flag must carry a consideration the request did not account for, in the
subject's terms, with what it would change; doc wording and "needs your call"
on classifiable text never qualify; triage per synthesize-doc-changes Step 2;
survey-time unconsidered reasons weighed under the existing Step 5 test;
`conflict-unresolved` entries still named, stated as competing intent and its
reason; ask about the person's words only when their meaning changes recorded
intent. Step 9 self-check gains a "questions" line. Paired edit in
synthesize-doc-changes Step 2 (see its ledger).

**Declined:** a new Step 5 pause trigger (would widen the gate the 07-23 entry
narrowed); edits to map-concepts-to-docs (its verdicts are doc-level and the
run reached synthesis with the right `partial-supersession`; its bias rule is
already tempered by `_shared/conflict-test.md`); edits to conflict-test.md
(shared by cascade-check, revise-doc, garden; its "stale, not in conflict"
rule already fits; the gap was sentence-level triage at write time).

**Regression answers:** 1 identify-then-synthesize — yes, unchanged. 2
archive — unchanged. 3 pause gate — yes, no trigger added; real conflicts
still named. 4, 5, 6, 8 — unchanged. 7 large updates proceed — yes. 9
settled cruft cleaned in-pass — reinforced: contradicted implementation
wording is that cruft even when the owner's referent is unclear.


## 2026-08-25 — Settled-authority contradictions punted to owner (Class B)

**Failure:** During an apply-to-docs episode, the survey turned up a June doc
(pipeline tool contract: `create_*` on an existing entity is a hard error)
contradicted since 2026-08-11 by in-force create-always-creates
(20260811184912), which the request explicitly reaffirmed. The executor scoped
it out ("the owner spoke about hub create semantics, not the pipeline's tool
handler"), left it unresolved, and reported it as "out of scope, worth a
separate look." Owner: the system mandates purging such docs; nobody should
have needed to ask.

**Class:** B — two texts permitted the reading: Step 5 trigger 1 framed every
contradiction as something "the user must address," with no carve-out for
contradictions with *settled* authority; and the cruft-verdicts pointer
appeared only as a "detection lens" parenthetical under the body-content rule.
(Small C promotion, owner-confirmed: in-pass cleanup of settled-authority
cruft is an invariant, not acceptable variance.)

**Diff:** One paragraph inserted into Step 5 trigger 1: *unresolved* means
genuinely contested authority; a doc contradicted by settled authority (the
request's intent, or an in-force doc it reaffirms) is neither a trigger-1
conflict nor a trigger-2 side-effect — it joins the impact set and is resolved
in-pass per `_shared/cruft-verdicts.md` (deprecate with Correction +
`superseded_by`, or REMOVE); never handed back as "out of scope" / "worth a
separate look"; the episode review records it post-hoc.

**Declined this pass:** editing map-concepts-to-docs' `conflict-unresolved`
definition ("need human judgment" is already correct — settled contradictions
don't) and cruft-verdicts' elective framing ("wants to apply"). Single
failure, one edit; revisit only if the punt recurs through a sibling skill.

**Regression answers:**
1. Identify then synthesize — yes; survey stays read-only, cleanup lands in
   the Step 6 batch.
2. Archive then extract — yes; unchanged.
3. Pause gate — yes, sharpened: contested conflicts and genuinely unintended
   impact still pause; settled cruft no longer masquerades as either.
4. Verbatim request body — yes; unchanged.
5. One episode review — yes; the edit explicitly leans on it (post-hoc
   signoff instead of pre-clearance).
6. Honest `--source` — yes; unchanged.
7. Large coherent updates proceed — yes; reinforced.
8. Current-work → `living` — yes; unchanged.

## 2026-08-04 — status:target default misuse (Class B + C)

**Failure:** apply-to-docs (and sibling writers) stamped nearly every
pre-implementation concept `status: target` because body-content rules said
"if implementation lags the model → target," and this skill runs minutes
before current work.

**Class:** B — quoted skill text permitted the bad reading. C promotion
(user-confirmed) — type fitness: principle/constraint/goal/requirement almost
never `target`; `target` is mainly for decision/component with explicit
weeks+/migration deferral. Default and ambiguity → `living`.

**Diff:** Added `_shared/status-living-vs-target.md`; rewrote body-content
pointers in apply-to-docs / synthesize / revise / ingest / reconcile; dropped
ingest's "prefer target when ambiguous"; added Step 9 status self-check.

**Ping-pong note:** ingest previously biased ambiguity → `target` against
stale-cluster drift from plan tone. Replaced that bias with per-concept
classification + shared deferral test (user-approved scope change).

**Declined this pass:** revising KB status-enum doc (`20260617212538`) —
separate docs episode.

**Regression answers:**
1. Identify then synthesize — yes; unchanged.
2. Archive then extract — yes; unchanged.
3. Pause gate — yes; unchanged.
4. Verbatim request body — yes; unchanged.
5. One episode review — yes; unchanged.
6. Honest `--source` — yes; unchanged.
7. Large coherent updates proceed — yes; unchanged.
8. New: current-work concepts born `living`; `target` only with explicit deferral.

---

## 2026-07-23 — Pause gate: conflicts / side-effects, not size (Class B + C)

**Failure:** After archival, apply-to-docs paused on 9 partial/cascade-extend
with **0 conflicts**, asking yes/no to proceed with the change the user had
just requested. User: the gate is for conflicts / unintended side-effects
(things not yet addressed), not a permission slip for expected work.

**Class:** B — Step 5 thresholds (`≥2` full / `≥4` combined) literally force
that rubber-stamp. C promotion — pause purpose narrowed; size alone must not
gate. (Also updates KB requirement `20260618000209`, which encoded the same
thresholds — skill+KB were aligned on the wrong proxy.)

**Diff:** Rewrote Step 5: invariant pause on `conflict-unresolved`; judgment
pause on unintended/out-of-scope impact; explicit ban on pausing solely for
large expected impact. Warning template reframed around *why this isn't just
proceeding*. Blast-radius survey still always runs.

**Regression answers:**
1. Identify then synthesize — yes; survey unchanged.
2. Archive then extract — unchanged.
3. Pause gate — yes under new meaning (conflicts/side-effects); old "pause on
   large radius" anchor deliberately retired.
4. Verbatim / honest source — unchanged.
5. One episode review — unchanged.
6. Honest `--source` — unchanged.
7. New: large coherent updates proceed without yes/no.

**Ping-pong note:** earlier same-day ledger left pause unchanged; this is a
deliberate scope change to the gate's purpose, not a flip-flop on an edit from
that pass.

---

## 2026-07-23 — Accurate --source + inherit root-over-decision + self-check (Class A)

**Failure:** `--source "user-request"` hardcoded for agent-authored archives;
extraction inherited identify without naming root-over-decision; close missed
batch smells.

**Class:** A (missing accuracy / self-check); inherits B/C fix from
identify-key-concepts.

**Diff:** Step 1b `--source` must describe actual material; `user-request` only
for user wording. Step 2 prompt names root-over-decision. Step 9 batch
self-check before close.

**Regression answers:**
1. Identify then synthesize — unchanged.
2. Archive then extract — unchanged; source string now honest.
3. Pause gate — unchanged.
4. Verbatim when input is user text — yes; clarified vs agent restatement.
5. One episode review — unchanged.
