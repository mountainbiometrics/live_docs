# Ledger — synthesize-doc-changes

Edit history for skill refinements. Newest first.

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
