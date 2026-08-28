# Ledger — cascade-check

Edit history for skill refinements. Newest first.

## 2026-07-28 — Restated-ownership repair (Class B)

**Failure:** Catalog membership edits cascaded by syncing restated capability
lists into dependents' bodies/summaries (a consumer store's coverage-audit removal).

**Class:** B — Step 5 + worked example explicitly endorsed updating restated
enumerations to the new list.

**Diff:** Step 5 restated-ownership repair (collapse to link, do not sync)
keyed off `_shared/doc-style.md`; worked example rewritten to match;
wide-cascade note reframed as singular-ownership smell. Owned-claims
invariant added in `_shared/doc-style.md`.

**Declined:** Hard atomicity (capability-per-doc) as an invariant.

**Regression answers:**
1. Two-pass separation — unchanged.
2. Inconsequential bias — strengthened for post-collapse list-only churn.
3. Frozen docs — unchanged.
4. Descendant-summary / garden-summarize — unchanged.
5. New: restated ownership collapses to link.
