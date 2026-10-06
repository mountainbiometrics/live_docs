# Conflict test — when a contradiction needs the owner

Single source of truth for every actor that issues a `conflict-unresolved`
verdict (map-concepts-to-docs, assess-blast-radius, revise-doc) or an
`incompatible` verdict (cascade-check), and for apply-to-docs's pause gate.
Read and apply this; do not paraphrase from memory.

## The rule

A doc that contradicts the new intent is a **conflict only if a why the
existing claim rests on argues against the intent.** Otherwise the doc is
stale, and the verdict is a supersession (partial or full): it is revised or
deprecated in the same pass, and the report says so.

Why: a `component` records what was designed and a `decision` records what
was chosen; neither is a reason on its own. "The store currently says X" is
never an argument against an owner who says "it should be Y, because Z."
Flagging that as a conflict hands the owner a question they already answered,
and trains the pass to defend the status quo instead of converging on intent.

## The test — run before every conflict verdict

1. **Name the reason on the new side.** The owner's or the request's stated
   intent, with its reason. If the request states a rule with no reason at
   all, ask for the reason (`context-request` / a clarifying question); that
   is not yet a conflict either.
2. **Walk upward from the contradicting doc.** Its `requires` and
   `belongs_to` chain, plus any `constraint`, `requirement`, `goal`, or
   `principle` its body cites as its why (`ldoc neighbors <id>`,
   `ldoc show` on each).
3. **For each why-doc found, ask whether its reason argues against the new
   intent.** Quote the sentence that does.
   - A reason found → `conflict-unresolved` / `incompatible`. Surface both
     reasons, quoted, so the owner rules between two arguments.
   - No reason found, or the why-doc agrees with the new intent →
     supersession. Revise the stale doc and cascade.
4. **Weigh the level, not the status.** A `level: requirement` why outweighs
   a `preference`. But a requirement that only restates the what is still not
   a reason.

## What is never a competing why

- The contradicting doc's own body or summary.
- A signpost or component summary that inherited the wording.
- "The code does it this way" or "it has always been this way."
- A `decision` whose body names no alternatives and no rationale (that doc
  is a `component` in disguise, per `doc-types.md`).

## Worked example (illustrative, not a template)

Owner: "retries must back off exponentially; a fixed interval hammers a
dependency that is already struggling." Store: a `decision` titled "Retry
Every Two Seconds", and the component summary above it restating that.
Walking up: the constraint the decision rests on says "the upstream service
rate-limits bursts from a single client." No why argues against the owner;
the constraint is the very reason the owner gives, and the decision's fixed
interval was one way of honoring it. Verdict: full-supersession of the
decision, cascade to the component summary. No conflict, no pause.

Contrast: the same owner request, but the decision rests on a requirement
saying "recovery must complete within five seconds of the dependency
returning." Exponential backoff can exceed that. Two reasons now argue, so
the verdict is `conflict-unresolved`, surfaced with both sentences quoted.

## Bias

Prefer supersession over conflict when no why-doc gives a reason: a flagged
non-conflict costs the owner a re-ruling. Prefer conflict over supersession
when a why-doc gives a reason, even a weak one: silently overriding a reason
is drift. This narrows the calling skills' "prefer conflict over a guess"
bias: a guess about *whether a why exists* is settled by walking the graph,
not by flagging.
