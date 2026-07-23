# Ledger — reconcile-changes

Edit history for skill refinements. Newest first.

## 2026-07-23 — Disambiguate why-priority + batch self-check (Class B + A)

**Failure:** Despite existing "abstract/why" bias, reconcile produced
decision-inventory first passes; close/review did not surface type-mix / naming /
level smells.

**Class:** B for Step 2 prompt ("rationale/why behind each decision"); A for
close self-check.

**Diff:** Rewrote priority blurb and Step 2 extraction prompt to mandate
root-over-decision (thin decisions, separate root concepts). Added pre-close
batch self-check (type-mix, labels, levels, source string). Updated checklist.

**Regression answers:**
1. Born-living, no pause — unchanged.
2. Abstract/why priority — yes, strengthened to root-over-decision shape.
3. Heavy dedup — unchanged.
4. Optional digest provenance — unchanged.
5. One episode review — unchanged.
6. Validate, no reindex — unchanged.
