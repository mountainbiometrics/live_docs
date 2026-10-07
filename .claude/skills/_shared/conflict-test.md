# Conflict test — same claim, then compare intent

Single source of truth for every actor that issues a `conflict-unresolved`
verdict (map-concepts-to-docs, assess-blast-radius, revise-doc) or an
`incompatible` verdict (cascade-check). Read and apply this; do not
paraphrase from memory. The intent comparison it applies is defined once, in
`facets.md`; this file says how to reach it and what verdict each outcome
gets.

## The rule

A doc that contradicts the new claim is **stale, not in conflict**, unless it
states the same claim at a higher intent than the change carries. "The store
currently says X" is never an argument against someone who now says "Y":
flagging that hands the person a question they already answered and trains
the pass to defend the status quo instead of converging on intent. Neither
verdict here refuses or pauses anything; both are a record of what the
change touched.

## The test — run before every conflict verdict

1. **Same claim?** A use-case, goal, or outcome beside a decision, principle,
   or component is two docs. Record both and `relates` them. That is the
   usual shape of "I want abc" next to "we should build xyz." Stop here when
   they differ: the verdict is `compatible` / `inconsequential`, with the new
   doc created.
2. **Which intent does the change carry?** The table in `facets.md`: the
   person's words in this episode are `requested`, a proposal they went along
   with is `chosen`, an agent's own judgment is `incidental`.
3. **Compare with the doc's intent** (the first word of its doc line; a
   missing intent is `incidental`).
   - **At or above it → supersession.** `partial-supersession` or
     `full-supersession` in a survey, `cascade-extend` / `cascade-full` in a
     blast-radius walk, `cascade` in cascade-check. Revise or deprecate the
     doc in the same pass. The reply conveys what changed (`facets.md`, "How
     to convey it").
   - **Below it → write beside.** `conflict-unresolved` in a survey,
     `incompatible` in cascade-check. The doc's assertion stays; the new
     claim becomes its own doc at the change's intent, `relates` to the doc,
     and the report names both. The pass continues.
   - **Frozen** (`deprecated` or `reference`) → the same verdict as "below",
     whatever the intents: a frozen doc is never rewritten.
4. **Name force in the reason.** `must` or `should` says how large the
   departure is. It never picks the verdict.

Walking upward from the contradicting doc (`ldoc neighbors <id>`, its
`requires` and `belongs_to`) is still how you find what else the change
touches, so that those docs are updated or named too. A why-doc found there
is more blast radius, not a vote. If the change states a rule with no reason
at all, ask for the reason (`context-request` / a clarifying question): that
is about grounding the new claim, not about the old one.

## What is never a reason to leave an assertion

- The contradicting doc's own body or summary.
- A signpost or component summary that inherited the wording.
- "The code does it this way" or "it has always been this way."
- A `decision` whose body names no alternatives and no rationale (that doc
  is a `component` in disguise, per `doc-types.md`).
- A `must` the person never set.

## Worked example (illustrative, not a template)

Person: "retries must back off exponentially; a fixed interval hammers a
dependency that is already struggling." Store: a `decision` titled "Retry
Every Two Seconds", `chosen`, and the component summary above it restating
that. Same claim (how retries are timed); the change is `requested`, the doc
`chosen`. Supersession: revise the decision so the new timing and the goal
it had left unstated (spare a struggling dependency) are both visible,
cascade to the component summary. The reply mentions that this replaces the
earlier two-second choice. No pause.

Contrast: a gardening pass finds the same decision stale against a newer
`incidental` component doc. The change is `incidental`, the doc `chosen`:
write beside. The component doc `relates` to the decision, the report names
both, and the walk continues. "Retries that spare a struggling dependency"
beside "retry every two seconds" is a goal and a decision, two docs, not a
conflict either way.

## Bias

Prefer two docs over a conflict when the statements are different claims.
Prefer updating over defending: a doc is a signpost for what was said, not a
reason to refuse what is being said now. A guess about *whether it is the
same claim* is settled by reading the doc, not by flagging.
