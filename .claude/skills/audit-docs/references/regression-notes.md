# Regression notes — audit-docs

Anchors for refinement. Properties a good run has; future edits must keep
permitting each.

## Known-good properties (v1, 2026-10-14)

1. **Writes nothing.** A run touches no doc, no flag, no session; its only
   artifact is the report.
2. **Blind pass precedes sourced pass.** Findings on register, descriptors,
   scope, type, why, and time-and-negation are recorded before the
   provenance source is opened; vocabulary, intent_basis, attribution, and
   fidelity are checked after.
3. **A finding is verifiable from the report.** Quote or field, check name,
   cited section (for `violates`), and a one-line passing version; the
   caller can confirm the defect and apply the fix without reopening the doc.
4. **Every doc gets a verdict line**, including clean ones.
5. **A decision's own chosen names survive.** A decision whose claim is a
   contract's field names, an enum's values, or a wire format, chosen among
   alternatives for a reason, is not flagged for naming them. Every other
   mechanism sentence, in any type, is a finding (doc-style, mechanism is
   not the claim). A scope
   boundary sentence ("budget rules belong to metering; auth guarantees X")
   is not flagged as negative space when the doc states what it does
   guarantee.
6. **`reads-as` stays distinct from `violates`.** Judgment findings state a
   consideration and carry no citation; two runs may differ on them.
7. **No question to the owner about wording.** The Considerations section
   is empty or carries a design question in the subject's terms.
