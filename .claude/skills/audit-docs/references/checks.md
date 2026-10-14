# Checks — the recurring failures and where each is governed

Read after the shared standards, never instead of them. Each check names the
failure as it recurs in this store's write passes, the tell that surfaces it,
and the shared file and section whose rule a `violates` finding cites. A
check with no governing section is judgment: tag it `reads-as` and state the
consideration.

## A. Register — `doc-style.md` §Plain register

- **Argument, not description.** The body justifies a conclusion between
  abstractions; no named actor does anything. Tell: the first sentence has an
  abstraction as subject and a property as predicate; a reader could not
  repeat the mechanism back.
- **Aphorism shapes.** An epigram (nominalized abstraction as subject, actor
  deleted, quotable on its own); antithesis cadence ("X, not Y" stacked
  through the doc where the contrast is not the decision); a closing sentence
  that restates the paragraph; a heading or title that states the claim.
- **Metaphor and synonym rotation.** A sentence that read literally does not
  state its claim; the same concept under two names in one doc or across the
  set. An established term with a metaphor origin (cascade, signpost) is a
  name and is exempt.
- **Compacted summary.** Every claim squeezed into fewer clauses instead of
  claims dropped. Tell: the summary is the body in miniature; a reader cannot
  say the doc's role from it.
- **Role-jargon and epistemic vocabulary** ("authoritative", "privileged",
  "the drafter") in place of showing who does what.

## B. Descriptors — `label-title-summary.md`

- **Label states the answer or a slogan**, or is a fragment ("The Policy
  Is"), or carries a meta suffix (Mechanism, Pattern, Model). Passing: a
  2–5 word Title-Case noun phrase naming the topic.
- **Title is the body's thesis compressed** rather than the working line an
  engineer would type.
- **Summary copies the body's first line**, runs past three sentences, or
  argues. Passing: role and coverage, selected not compacted.

## C. Vocabulary — `label-title-summary.md` §Prefer the source's vocabulary; `doc-style.md` §One name (pass 2)

- An agent-coined handle or term where the source names the thing; a term
  the person rejected. Tell: the term appears in the doc and nowhere in the
  provenance source.

## D. Implementation in the claim — `cruft-verdicts.md` §The detection lens, §incidental vs subject; `doc-style.md` §Existence is a facet

- **Code mirroring.** Function, module, table, column, framework-artifact
  names, or carrier mechanics in a claim body outside `## Implementation`.
  Instrument: strip the name; if the claim still makes sense, the name was
  incidental. Second instrument: would this still be knowable if the
  implementation were rewritten?
- **Existence claim.** "X is not built yet", "no X exists", "X is implemented
  in Y" in a claim body. The facet `realization` owns this.
- **Mechanism in a claim body** — `doc-style.md` §Mechanism is not the
  claim. Any sentence stating how the code achieves the claim (which layer
  constructs a value, which function receives it first, who calls whom, what
  a field or function is called), in any doc that is not a `decision` whose
  claim is that mechanism chosen among alternatives. No survival test: the
  sentence goes, whether or not the claim reads better with it.
- **Fact outside the claim** — same section. A body states as fact
  something its own claim does not assert: another doc's claim, what the
  code does, what a neighboring context or transport does. Passing version:
  a link to the owning doc, or deletion.
- **Unowned mechanism disagreement** — same section. Two or more docs
  narrate the same mechanism differently and no decision in the set records
  it as a choice. One finding per doc, passing version without the
  mechanism; never a Consideration, never a passing version that picks one.
- **Commanding prose** — same section. "must", "never", "only", "always" in
  a body about anything but the doc's own claim. The claim's binding
  strength is its `force` facet.
- **Coupled mechanism.** A goal, use-case, requirement, principle, or
  constraint that names the mechanism a decision in the set owns ("signs
  members in by magic link" in a use-case) is the first check above, tagged
  `violates`; the set-level note names the owning decision so the caller
  can link it.

## E. Scope — `doc-types.md` §Body ceilings, §Two rules that apply to a decision; `doc-style.md` §Owned claims

- **Body beyond the descriptors.** The body decides or asserts something the
  label, title, and summary do not name (`reads-as`; cite the descriptor and
  the overreaching passage).
- **Two concepts in one body.** Unrelated sections, a compound title, a body
  over its type's ceiling (`ldoc validate` reports the ceiling).
- **Restated owned claim.** A membership set, catalog, or rule another doc
  owns, restated instead of linked.
- **Decision at the wrong level.** A decision with no `belongs_to` that binds
  one subtree, or placed under a subtree it does not govern
  (`belongs-to-placement.md`).
- **Duplicated rule across the set (judgment).** The same rule asserted by
  two docs from two sides. Propose the owner.

## F. Type — `doc-types.md` §The "is this really a decision?" ladder, §The why-chain

- A `decision` that says a thing exists (component), tells how to work
  (guide), or cannot be restated as "X over Y because Z".
- A norm (principle, constraint, requirement) with no goal or use-case above
  it, when the purpose is in the set or the source.
- A root (principle, constraint, requirement, goal) carried only as rationale
  prose inside a decision's body, with no doc of its own.
- `requirement` versus `constraint` versus `goal` by the typing test
  (property that must hold; limit not to cross; outcome to reach).

## G. The why — `doc-types.md` §Cross-cutting: every doc carries its why; `doc-style.md` §New principles and decisions are never born isolated

- A what with no why (headings excepted).
- A why that is the what restated ("so that reads are scoped" on a doc whose
  claim is that reads are scoped).
- A principle or decision with no `requires` and no `relates` on a topic the
  store already has opinions about.

## H. Time and negation — `doc-style.md` §No negative-space, §No deferral or plan language, §The body is not a changelog, §Clarification shortens a doc

- Negative-space: what the thing is not, what was ruled out, what a reader
  might assume.
- Deferral or plan markers: "deferred", "not yet", "for now", "later",
  "phase", "v1", "at launch" used as a schedule rather than a fact of the
  design. A stop-gap is named once as a stop-gap on an `incidental` decision.
- Changelog shape: update or correction paragraphs under an opening now
  false; a revised doc that grew without its `--note` saying what it gained.

## I. Facet honesty — `facets.md` §intent, §The evidence rule, §realization

- `intent: requested` or `chosen` without an `intent_basis` quoting the
  person's own words for this claim; a whiteboard-settled or agent-proposed
  claim recorded as `requested` (pass 2 against the source).
- `realization` that disagrees with what the body or `## Implementation`
  says; `force: must` on a claim the source states as a preference.

## J. Attribution — `doc-style.md` §Plain register (actors); `facets.md` §The evidence rule (pass 2)

- A body saying the person decided or said something the source does not
  show; an agent's inference presented as the person's statement.

## K. Domain versus scope — `domain-tagging.md` §scope-first

- A batch where every doc carries the same `domain` and the concern lives
  inside one `scope`; a domain that names the batch's subsystem rather than a
  cross-scope concern.

## L. Signposts — `doc-types.md` §heading; `garden-summarize` (orientation)

- A heading or parent whose body lists its children instead of orienting a
  reader among them; a parent of a claim type whose body carries no claim of
  its own.
