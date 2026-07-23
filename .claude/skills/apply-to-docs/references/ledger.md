# Ledger — apply-to-docs

Edit history for skill refinements. Newest first.

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
