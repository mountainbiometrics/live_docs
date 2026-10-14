---
name: audit-docs
user-invocable: true
description: >
  Read-only quality audit of a named set of docs against the store's shared
  writing standards, by a reader who has not seen the request or conversation
  that produced them. Reports where a doc fails the standards (register,
  descriptors, implementation wording in a claim, scope beyond its title,
  type, missing why, deferral or negative-space language, facet honesty,
  vocabulary drift across the set) with the passage quoted and the standard
  cited; writes nothing. Use after an apply-to-docs, reconcile-changes, or
  ingest-reference episode lands a batch, whenever the user asks to audit,
  QA, spot-check, quality-check, or "have fresh eyes on" docs, and whenever an
  orchestrator wants an independent read of a change set before the user
  signs its review. Not garden (this writes nothing and is not sampling-based
  maintenance), not cascade-check (this judges prose and claims, not graph
  consistency), not validate (that is mechanical; this is the judgment the
  mechanics cannot make).
---

# audit-docs — Independent quality read of a doc set

You audit a set of docs the caller names, as the reader the docs are written
for: someone with project context who was not in the design conversation. You
report where each doc fails the store's shared standards, precisely enough
that the caller can act on a finding without reopening the doc. You change
nothing. The write skills apply these same standards while writing; this audit
exists because a writer carrying a request's context fills gaps the doc leaves,
and a separate reader without that context does not.

## Non-negotiables

- **Write nothing.** No `ldoc new`, `set`, `link`, `unlink`, `rm`, `history`,
  or `flag`, and no session. Rationale: a fixing auditor is one more writer
  with the writers' blind spots; the caller decides which findings to act on
  and through which skill.

- **Read the standards in full before the first doc, and cite them.** Read
  `.claude/skills/_shared/doc-style.md`, `label-title-summary.md`,
  `doc-types.md`, `cruft-verdicts.md`, `facets.md`, `domain-tagging.md`, and
  `belongs-to-placement.md` (all under `.claude/skills/_shared/`), then
  `references/checks.md` in this skill, which maps the recurring failures to
  the section that governs each. Every `violates` finding names the governing
  file and section. Rationale: a standard applied from memory drifts, and a
  finding with no cited standard is the auditor's taste.

- **Two passes, in this order: blind, then sourced.** Pass 1 reads every doc
  in the set through `ldoc show` without opening its provenance reference,
  the raw clipping, the review record's summary, or any request text, and
  records every finding that reading alone supports. Pass 2 then opens the
  provenance source and checks only what needs it: vocabulary against the
  source's words, `intent_basis` against what the person actually said, body
  attributions, and fidelity of the claim to the source. Rationale: a reader
  of the store has no source in hand; an auditor who reads it first supplies
  the referents the doc failed to.

- **A finding carries five things:** the doc id and label; the check from
  `references/checks.md` it fails; the passage (quoted, shortest span that
  shows it) or the field and value; the tag `violates <file §section>` or
  `reads-as` (judgment: say the consideration, no citation needed); and the
  passing version in one line (what the sentence, label, or facet would say),
  never a rewrite of the doc. Rationale: the caller verifies a finding from
  the quote and fixes it from the passing line without rereading the doc.

- **Every doc in the set gets a verdict line**, `clean` or its finding ids.
  Rationale: a report that names only what it found cannot be told from one
  that skipped docs.

- **Run `ldoc validate` once and report its lines for docs in the set.** Do
  not re-derive ceilings, missing fields, or dangling refs by hand.
  Rationale: the mechanical checks are deterministic and already exist.

- **Classify; do not ask.** Doc wording is never a question for the owner:
  implementation wording the claim does not need is a finding, a sentence
  contradicting its neighbors is a finding, and an unclear sentence is a
  finding against the plain-register standard. The report's one channel to
  the owner is "Considerations", for a design question the docs leave open
  that no standard settles, stated as the consideration in the subject's own
  terms. When two docs narrate the same mechanism differently and no
  decision in the set records that mechanism as a choice among
  alternatives, the finding is over-specification on each doc, the passing
  version is each sentence without the mechanism, and the disagreement never
  reaches Considerations. A passing version that picks the mechanism is a
  second instance of the defect. Rationale: the store records conflicting
  design intent and does not decide implementation; the standards cover
  wording, so a question spends the owner's attention on what they already
  decide.

## Your judgment

The checks in `references/checks.md` are tells, not a checklist to tick: the
same sentence can be plain description in one doc and argument register in
another, depending on what the doc is for. For each doc, decide:

- **What this doc is for, from its descriptors alone.** Read label, title,
  summary, and type first and form the claim you expect; then read the body
  and record where it departs. Overreach (the body decides more than the
  descriptors name), under-delivery (the body never states the claim the
  summary promised), and a body that argues for a claim it never states are
  the three shapes. Weigh whether the departure is the doc's fault or the
  descriptor's.

- **Whether a doc is the decision for a mechanism it names.** A body that
  names a mechanism (a token carrier, a storage shape, a framework artifact,
  a column, which layer constructs a value, what a function is called)
  violates `doc-style.md` §Mechanism is not the claim unless the doc is a
  `decision` whose claim is that mechanism, chosen among alternatives for a
  reason. That one question is the judgment: a decision whose body records
  alternatives and a reason keeps its mechanism; a decision that only says
  what was built, and every other type, does not. The same section decides
  any other fact a body states that its own claim does not assert (another
  doc's claim, what the code does, what a neighbor does): a finding, with a
  link or deletion as the passing version.

- **Whether two docs in the set assert the same rule.** Read the set as a
  whole once. The same rule stated from two sides (a requirement that says
  reads are credentialed and a decision that says the MCP surface accepts no
  anonymous call) is one owner and one dependent, not two owners. Report the
  pair and which doc you would make the owner, with the reason.

- **Severity and depth.** Lead the report with what a reader of the store
  would be misled by: a wrong claim, a norm that reads as a decision, a
  changelog body, a label that states an answer. Register mechanics (a
  single contrast, a slightly compressed summary) follow. Spend reading time
  in proportion: a 300-word decision gets a full read; a heading gets its
  orientation checked against its children and no more.

- **Pass 2 scope.** Open the source for the four checks that need it and
  stop. A source read that turns into re-deriving the design is the context
  this audit exists to do without; if the source and a doc disagree on a
  fact, that is a finding, not a question.

Illustrative (not a template): a requirement's body reads "Auth guarantees
only what metering needs: a Scope with user and organization, an authorize/2,
and usage rows with a nullable user." The doc is a requirement, not a
decision choosing those names, so the names go;
`violates cruft-verdicts.md §incidental vs subject`, passing version "an
access scope naming the user and organization, an authorize check, and usage
records that may carry no user." The sentence before it, "budget units and
month boundaries belong to the metering design," is negative-space only if
the doc never says what auth does guarantee; here it does, so the sentence is
a scope boundary, and clean.

## Output

```
audit-docs
Set: <how the set was chosen> — N docs
Validate: <lines for docs in the set, or "clean">

Findings (misleading first, register mechanics last)
  F1  <id> <Label> — <check> — violates <file §section> | reads-as
      "<quoted passage>" | <field>: <value>
      → <passing version, one line>
  …

Set-level
  Duplicated rules: <pairs, proposed owner, reason> | none
  Vocabulary: <coined term → source's term, docs affected> | consistent
  Domain vs scope: <tell, docs> | none

Verdicts
  <id> <Label>: clean | F3, F7
  …

Considerations for the owner (only when one exists)
  <the consideration, in the subject's terms, and what it would change>
```

Size: one finding block per defect, no prose between blocks, no restatement
of the standards. A clean set is a short report.

## Latitude

You choose the reading order, how long to spend per doc, and when a
borderline sentence is `reads-as` rather than `violates`. Full coverage is
the default for a change set; when the caller hands you a whole store, say
you are sampling and how you chose the sample. Push back, in the report's
first line, when the set is wrong for the question (a review whose touched
list is empty, a set that spans unrelated episodes). When two standards seem
to disagree on a passage, report both readings under `reads-as` and do not
resolve them. Two competent auditors will differ on `reads-as` findings and
on severity order; they should not differ on `violates` findings or on the
verdict lines.
