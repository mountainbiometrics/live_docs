# Ledger — identify-key-concepts

Edit history for skill refinements. Newest first.

## 2026-07-23 — Root-over-decision invariant (Class B + Class C promotion)

**Failure:** Panelists reconcile/apply inventoried decisions as first-class docs
with rationale as body prose; user had to mid-flight correct toward
principles/constraints/goals as first-class, decisions as thin dependents.
Reiterated: live_docs is a why-lens, not an ADR dump; decisions are useful for
modeling relations but the nonrecoverable roots are the prize.

**Class:** B (reconcile/identify framing treated "rationale behind each decision"
as belonging inside the decision) + C promotion (user confirmed
root-over-decision is invariant-strength — unwilling to accept variance).

**Diff:** Added Step 1b invariant "Root-over-decision" with rationale (recoverable
vs nonrecoverable; re-evaluation needs the why-web). Explicitly forbids collapsing
roots into decision Asserts. Forbids inventing unsupported why-chains. Companion
clarification in `_shared/doc-types.md`: "prefer decision over principle" is a
single-claim typing rule, not permission to skip separable roots.

**Declined:** Mandating a 5-whys / fixed-depth procedure (user: illustrative only).

**Regression answers:**
1. Durable claims not implementation steps — yes, still required.
2. Presupposed roots fair game when text depends on them — yes; narrowed to
   "unintelligible without them," still permitted.
3. Doc-types ladder — yes; typing rule preserved with dual-extract clarification.
4. No KB queries/writes — unchanged.
5. Splitting opt-in — unchanged.
