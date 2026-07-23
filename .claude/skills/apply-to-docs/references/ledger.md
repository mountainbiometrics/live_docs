# Ledger — apply-to-docs

Edit history for skill refinements. Newest first.

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
