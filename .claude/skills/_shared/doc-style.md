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
  what's temporarily not true (it isn't built yet — that is the doc's
  `realization`, `planned` or `deferred`; see `facets.md`).
- If a doc genuinely needs to record that an idea was considered and
  explicitly rejected (not merely "not yet"), that's a `decision` with a real
  rationale, not a goal with deferral hedging.

## Stop-gaps are `incidental`, and say so honestly

Sometimes the right move today is a placeholder — good enough to unblock work,
known not to be the durable design. Record it as a `decision` with
`intent: incidental` (a provisional adoption the person let happen — see
`facets.md`), and say plainly in the body that it's a stop-gap:

- Name the actual need the stop-gap satisfies ("a worker's deployment region
  must be stored somewhere and handed to the monitoring dashboard").
- Name the stop-gap plainly ("for now, that's a single free-text tag on the
  worker record").
- Do not write the stop-gap up as if it were the solution to the whole
  problem — a reader should come away knowing this is provisional without the
  doc using deferral language to say so (the honesty comes from calling it a
  stop-gap once, not from hedging every sentence).

## Existence is a facet, not prose

A claim body never says what is or is not built. Whether a claim is built is
the `realization` facet, and how it is built is the `## Implementation`
section (`facets.md`). A sentence such as "no eviction policy exists yet" goes
false when the code changes, nothing re-checks it, and a reader takes it for
part of the doc's claim.

## Mechanism is not the claim

A claim body states its own claim and the reason for it. It does not state
how the code achieves the claim: which module constructs a value, which
function receives it first, which layer calls which, what a field, table, or
function is called. The one doc that names a mechanism is a `decision` whose
claim is that mechanism, chosen among alternatives for a reason. A mechanism
that exists because someone built it that way is not a decision and gets no
sentence in any claim body; its place, when it is worth recording, is the
`## Implementation` section (`facets.md`). That the claim reads more
concretely with the mechanism in it is not an exception.

The descriptors are under the same rule. A title, label, or summary that
names a mechanism is the same defect, and it does not make the doc the owner
of that mechanism: only a decision owns one. A non-decision doc whose title
names a mechanism is retitled to its claim, and the owned-claims rule below
applies to claims, never to mechanisms. For a `component`, the claim is what
the thing is responsible for and why it exists. What it issues, what it
calls, what it writes to, and which direction its dependencies run are
mechanism, or the claim of the principle or decision that set them, and are
not in its body. The rule is applied to every sentence, not to the ones that
resemble the examples here.

The rule is a boundary of responsibility, and it covers more than code: a
body states as fact only what its own claim asserts. What another doc claims
is reached by a link to that doc, never restated here as fact (owned claims,
below). What the code does is the `realization` facet and the Implementation
section. What a neighboring context, transport, or component does is that
doc's claim. A sentence stating a fact the doc is not responsible for reaches
outside it, and goes.

Why the rule is strict: downstream, an agent reads an indicative sentence
("the transport then issues the token", "every context function takes the
scope first") as a settled decision and builds to it, when the store exists
to surface conflicting design intent and does not dictate implementation.
Across docs, two bodies narrating the same mechanism from their own vantage
drift apart, and the drift reads as a design conflict where there is none:
each claim is still true, and one implementation satisfies all of them.
When docs disagree on a mechanism no decision records, remove it from each;
do not arbitrate, and do not ask the person which is right. The claim's
binding strength is its `force` facet; prose that commands ("must",
"never", "only") adds nothing a reader can act on and is read as doctrine.

## The body is not a changelog

A doc states its current claim. When the claim changes, the body, summary, and
title are rewritten to say the new thing, and every sentence that became false
is removed. Appending an update or correction paragraph under an opening that
is now false leaves the old claim as the first thing a reader meets, with the
summary still pointing at it. What changed goes in the mutation's `--note`.

## Clarification shortens a doc

When a revision folds in material that clarifies or narrows what a doc is
about, rewrite the doc to the clearer understanding instead of adding the new
material to the old text. The clearer understanding usually needs fewer words:
sentences that hedged around a question now settled, drew a distinction the
settled design no longer needs, walked through an example the plain claim now
makes obvious, or recorded how the understanding was reached lose their reason
to exist. A doc that grows every time its subject gets clearer has been
appended to, not revised. Growth is legitimate when the subject itself gained
something (a new reason, a case the claim now covers), and it is the exception.

Weigh, as you rewrite (a judgment, not a length target):

- Read the whole body against the new understanding, not only the part the new
  material touches. A sentence can be true and still be redundant (the new
  statement covers it), hedged (it qualifies against an alternative now ruled
  out), or merely historical (it says how the view developed). Remove those;
  falseness is not the only reason to cut.
- Examples, lists, and context paragraphs stay for what a reader needs to
  understand the claim now. An example that propped up a vague claim can go
  once the claim is stated plainly. A list about to gain another item is a
  prompt to ask whether the clearer understanding states it as one rule, or
  whether another doc owns the list and this one should link it (owned claims,
  below).
- A body already past its type's ceiling (`doc-types.md`) should come out of a
  revision shorter, or be split; adding to it needs a reason the doc cannot do
  without. A signpost reaches new members through their `belongs_to` edges:
  rewrite its orientation to cover them rather than adding a paragraph per
  arrival.
- Shorter means selection, not compaction: drop the sentences the new
  understanding makes unnecessary, and do not squeeze the remaining claims into
  denser clauses (plain register, above).

What survives the cut:

- The why: the reason, constraint, or purpose the claim rests on, and a
  rejected alternative when it is the direct contrast that explains the choice.
  A rationale that still holds stays even when it is long.
- Detail that is the doc's subject (`cruft-verdicts.md`, incidental vs. the
  subject).
- What records where the doc came from and what it connects to: `history`
  entries (append-only), provenance and other edges, a deprecated doc's
  `## Correction` section, and the `## Implementation` section, which is
  refreshed on its own terms (`facets.md`).

When a revised body comes out longer than it went in, the mutation's `--note`
says what the doc gained that needed the length, so a reviewer can tell an
added claim from accretion.

## The `## Implementation` section is exempt

A body may carry a `## Implementation` section describing how the claim is
currently implemented. That section is volatile and exempt from the rule that
bodies carry the why and not the *what* the code encodes (`doc-types.md`,
`cruft-verdicts.md`); what it is and when it is refreshed is `facets.md`
(realization). The rest of the body stays the claim and its why, in this
file's register.

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
