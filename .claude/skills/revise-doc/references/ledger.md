# Ledger — revise-doc

Edit history for skill refinements. Newest first.

## 2026-10-14 — Clarification shortens a doc (Class B)

**Failure:** see synthesize-doc-changes ledger, same date: revisions folded
clarifying material in by appending, so docs grew as their subject got clearer.

**Class:** B. Step 3 quoted: "Make the minimum change that satisfies the
caller's intent" and "No gratuitous reformatting, no refactoring beyond
scope" read as forbidding removal of true-but-now-redundant text; the rewrite
paragraph licensed removing only sentences that "became false."

**Diff:** Step 3: "minimum change" → "the change the caller's intent calls
for, and no unrelated change"; new paragraph: falseness is not the only reason
to cut, clarifying changes usually shorten, growth is explained in `--note`,
pointing at `_shared/doc-style.md` "Clarification shortens a doc"; scope line
now says removing text the change made unnecessary is in scope. Step 4
classification untouched.

**Regression answers:** 1 dedup/conflict scan, 2 history entry, 3 cascade, 5
status — untouched. 4 claim and why — kept: the shared section lists the why
and history entries as what survives.

---

## 2026-08-04 — Body-content status rule → shared deferral test (Class B)

**Failure:** Body-content said "implementation lags → `status: target`,"
teaching the same over-use as apply-to-docs / synthesize.

**Class:** B — quoted rule permitted the bad reading.

**Diff:** Body-content anti-patterns point at
`_shared/status-living-vs-target.md`; default `living`.

**Regression answers (reconstructed):**
1. Dedup/conflict scan before substantive edit — unchanged.
2. History entry on substantive change — unchanged.
3. Cascade after substantive change — unchanged.
4. Bodies claim/why; status carries only explicit deferral — yes under new rule.
