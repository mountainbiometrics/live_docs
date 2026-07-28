# Regression notes — synthesize-doc-changes

Anchors for refinement. Reconstructed 2026-07-23; replace with cited happy-path
outputs when available.

## Known-good properties (must keep permitting)

1. **Coherent state, not minimal patches.** Rewrite misleading prior text; do
   not leave contradictory statements coexisting.
2. **Provenance edge, not body taxonomy.** Every new doc gets `--provenance
   <anchor>` (schema edge). live_docs itself does not define body-line
   provenance tiers (`user-stated` / `user-confirmed` / `agent-inferred`) — those
   were a consumer-store convention.
3. **Level: incidental when ungrounded.** Claims without an explicit
   requires/belongs_to/provenance/source anchor stay `incidental`.
4. **Labels name the subject.** Apply `_shared/label-title-summary.md`; no
   meta-jargon suffixes; noun-phrase handles.
5. **belongs_to ≠ requires.** Nest clusters under defining parents; do not flatten
   to broad signposts out of false caution.
6. **Body states the claim and why** — not implementation narration, session
   play-by-play, or absence/history.

## Known failure (2026-07-23 panelists)

Synthesis canonized agent-coined labels ("Token Quantum Turns", "Harm Ledger",
"Per-Pair Panelist Servers", "Thesis Test") over session/user vocabulary
("with your x number of tokens", "panelist-servers", "theories"). Separately,
consumer-store body provenance lines were blanket-stamped `user-stated` including
for agent-articulated derivations. Also: unconfirmed agent claims shipped as
`level: requirement` because the old incidental rule keyed off "missing
provenance edge," which never happens when every new doc gets `--provenance`.

## Newly discovered good-output properties (2026-07-23)

7. **Incidental is reachable.** Unconfirmed agent articulations default to
   `level: incidental` even when they carry a provenance edge to a digest/request.
8. **Source vocabulary for handles.** Labels/titles prefer words from the
   provenance material over agent coinages.
9. **Anchor from panelists QA** (`~/projects/panelists` review `20260722230917`,
   signed): labels must name the subject; thin summaries/bodies rewritten to
   say what the thing is and why it matters; delete implementation-recoverable
   docs — these are positive naming/shape examples, not a provenance-tier spec.

## Newly discovered good-output properties (2026-07-28)

10. **Owned claims linked, not restated.** Dependents cite catalogs/membership
    sets via `[[owner]]` (+ edges); they do not re-enumerate the owner's list
    in summary or body. Soft-atomic cleanup in sinai (`20260625215253`,
    `20260622220247` → link `20260622220218`) is the positive example.
