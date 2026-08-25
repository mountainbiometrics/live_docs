# Doc style — the shared discipline

Single source of truth for the writing-discipline gaps that neither
`label-title-summary.md` (titles/labels) nor `cruft-verdicts.md` (stripping
implementation detail from a body — applied proactively at write time by
`apply-to-docs`, `ingest-reference`, `revise-doc`, and `synthesize-doc-changes`,
not only during gardening) already own. Read and apply this alongside those
two; do not paraphrase from memory.

## Plain register

Write the way you would explain the system to a colleague: say what the
thing is, who does what, and what it is for. The recurring failure mode is
docs written as *arguments* — justifications of a design conclusion,
conducted between abstractions — instead of *descriptions* of the thing
decided. An argument can only be parsed by a reader who already knows the
design; a description is what the reader came for.

**Describe; don't argue.**

- Open with what the thing is or what happens: named actors doing things,
  not properties of abstractions. The why follows the what, in the body.
- A summary states the concept's role and what the doc covers — never the
  body's argument compressed. Distill by selection (drop claims from the
  summary; the body owns them), not compaction (every claim squeezed into
  fewer clauses — it reads as density, but the information is
  unrecoverable). Summaries are surfaced verbatim in reviews, search, and
  indexes, so they are held to this hardest.
- Build each sentence from what a reader with project context — but without
  the design conversation — already holds, adding one new idea at a time.
  The acceptance test: that reader can repeat the mechanism back after one
  read.
- Actors get plain nouns. Don't promote people into role-jargon a sentence
  doesn't need, and don't substitute epistemic vocabulary ("authoritative",
  "privileged") for showing the mechanism.
- The argument register also resists checking: a claim stated abstractly
  can contradict a neighboring doc with nothing concrete to check it
  against. If a plain rewrite exposes a possible contradiction, report it
  as a finding rather than wording around it.

**Mechanics** — necessary but secondary; enforcing these without the stance
produces polished pomposity:

- One name per concept: reuse the established term (lexicon, source, or
  owning doc) every time the concept appears; never rotate synonyms —
  search, wikilinks, and cascade key on terms. An established term whose
  origin is a metaphor is a name; keep it.
- No new metaphor or imagery: a sentence read literally, word by word, must
  state its claim.
- Watch for aphorism shapes: epigrams (a nominalized abstraction as
  subject, the actor deleted, quotable), closing punchlines that restate
  the paragraph, antithesis cadence ("X, not Y" stacked through a doc — a
  contrast earns its place only when it is the decision itself), and maxim
  headings or thesis titles (headings and titles name topics; the claim
  lives in the body, once).

**Example** (illustrative, from one consumer store's cleanup — the same
claim, two stances):

Argument register:
> The drafter sees exactly what the capability sees, so its answer is
> peer-level at best, and a draft accepted without correction sets the
> target at today's level.

Description:
> An LLM drafts a case's expectations from the premise; that draft is the
> initial baseline. Human refinement on top of it is what makes the
> expectation a target that can evolve.

The first justifies a conclusion between abstractions; the second says who
does what and what it is for. When in doubt, write the sentence you would
say out loud — speech forces the referents and the purpose to be stated.

## No negative-space documentation

**We don't document what things are not.** A doc states positively what a
thing *is*; it does not spend space cataloguing what it isn't, what was
rejected, or what a reader might mistakenly assume. Two situations look
similar but resolve differently:

- **A genuinely open question** ("does the cache invalidation policy apply
  per-key or per-namespace?") may be stated as an open question, briefly,
  because that is itself a fact worth recording — the design is unsettled
  here. State it as a question, not as a list of ruled-out answers.
- **A settled decision framed defensively** ("the retry queue is not a
  dead-letter store, is not a general job queue, and is definitely not a
  scheduler") should be rewritten as the positive claim alone ("the retry
  queue holds only messages awaiting their next backoff window"). If the
  positive claim is genuinely ambiguous without the negative framing, that's a
  sign the positive claim itself isn't clear yet — fix the claim, don't prop it
  up with exclusions.

Considered-and-rejected alternatives may appear in a `## Correction` section
on a *deprecated* doc (that's the historical record), or as a one-line aside
inside a decision's rationale when the rejected alternative is the direct
contrast that explains *why* ("X over Y because Z" — see `doc-types.md`'s
decision ladder). They should not become the doc's main content.

## No deferral or plan language

This extends the store's no-plan-markers discipline (no "phase 3," "v1,"
"slice N" in doc prose) to a specific recurring failure: a doc that states a
real, current need but wraps it in language about *when* or *whether* it will
be addressed — "deferred," "not yet designed," "currently out of scope,"
"we're punting on this for now."

- A `goal` doc states the need, period: *"The service will need to support
  per-tenant rate limiting."* Full stop. No sentence about what isn't planned,
  what's deferred, or what phase this is.
- Deferral language creates a trap for future agents: a doc that says "we
  discussed X but decided to defer it" reads, months later, as a standing
  decision *not* to build X — an agent asked to build it will cite the doc
  back at the person asking. Say only what's true (the need exists) and never
  what's temporarily not true (it isn't built yet — that's what the codebase
  and task tracker already show).
- If a doc genuinely needs to record that an idea was considered and
  explicitly rejected (not merely "not yet"), that's a `decision` with a real
  rationale, not a goal with deferral hedging.

## Stop-gaps are `incidental`, and say so honestly

Sometimes the right move today is a placeholder — good enough to unblock work,
known not to be the durable design. Record it as a `decision` at
`level: incidental` (claim authority is low / provisional — see
`synthesize-doc-changes` level classification: incidental is the default for
unconfirmed agent articulations and stop-gaps, not a synonym for "missing
provenance edge"), and say plainly in the body that it's a stop-gap:

- Name the actual need the stop-gap satisfies ("a worker's deployment region
  must be stored somewhere and handed to the monitoring dashboard").
- Name the stop-gap plainly ("for now, that's a single free-text tag on the
  worker record").
- Do not write the stop-gap up as if it were the solution to the whole
  problem — a reader should come away knowing this is provisional without the
  doc using deferral language to say so (the honesty comes from calling it a
  stop-gap once, not from hedging every sentence).

## Owned claims are linked, not restated

When another doc already owns a claim — especially a membership set, catalog,
or enumeration — dependents MUST reference it via `[[id]]` (and edges), not
restate the list or claim in their own summary or body. Reason: restated
ownership is how one atomic edit becomes an N-doc prose sync; cascade then
"fixes" copies instead of edges. If you catch yourself updating the same
enumerated set in more than one doc, stop — collapse the copies to links and
leave one owner. The owner's body (not every dependent's summary) is where
membership detail lives.

## New principles and decisions are never born isolated

Before minting a new `principle` or `decision`, search the store for existing
docs that already state part of the same idea from a different entry point —
prior architectural discussions, adjacent subsystem decisions, earlier passes
at the same tension. A genuinely new idea that turns out to restate or extend
something already in the store should `requires`/`relates` to it and defer to
it in the body, rather than restating it as if from nothing.

**Signal that this step was skipped:** a new principle doc with zero
`requires` and zero `relates` edges, on a topic that isn't obviously novel to
the store (retry/backoff policy, cache invalidation, access-control layering —
things any mature system has opinions about already). Treat that as a red
flag worth a second search pass before accepting the doc as complete, not as a
finished result.

This is a creation-time discipline, distinct from `garden-densify` (which
repairs *already-written* docs missing edges after the fact) — the aim here is
to not create the gap in the first place.
