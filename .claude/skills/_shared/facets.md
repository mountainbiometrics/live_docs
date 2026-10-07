# Facets — the shared definition

Single source of truth for the facets that say how a doc's claim stands:
`intent` (with `intent_basis`), `force`, `realization` (with
`realization_refs` and `realization_verified`), `imposed_by`, and `status`.
Every actor that creates, revises, gardens, or cascades from a doc — or acts
in code on one — reads and applies this. Read and apply this; do not
paraphrase from memory.

Each facet answers one question, and they do not follow from one another:

| Facet | Question |
|---|---|
| `intent` | What did the person do to make this claim exist? |
| `force` | How hard does the claim bind? |
| `realization` | Does the thing the doc claims exist in the implementation? |
| `imposed_by` | What makes this claim hold? |
| `status` | Where is the doc in its lifecycle? |

Which facets a type carries (required, forbidden, optional) and which
`requires` edges it is expected to have live in `doc-types.md`; this file says
what each value means and what it permits. Listings show intent as the first
word of every doc line and force and realization as trailing tags, so an agent
can decide whether a doc binds it without opening the doc. That only works if
the values are honest.

## The most common failure mode this prevents

**Recording a claim at an intent the person never gave it.** An agent proposes
something, the person does not object, the change gets committed, a review is
signed — and the doc lands as though the person asked for it. From then on,
every agent treats an agent's suggestion as the person's own decision and
refuses to change it. This is what makes agents refuse iterative changes on
the grounds that the shape was ratified. A commit, a merged change, a signed
review, or silence is the person letting a claim happen; that is
`incidental`, however solid the claim and however much code stands behind
it.

## Default

- `intent: incidental`. When you do not know what the person did, it is
  `incidental`.
- `status: living`.
- `force`, `realization`, and `imposed_by` have no default: assess each claim
  on the tests below. When the source does not say a normative claim is a
  rule, it is `should` — a `must` the person never set blocks agents exactly as
  inflated intent does.

## `intent` — what the person did to make this claim exist

| Value | The person… |
|---|---|
| `requested` | brought this claim forward themselves. |
| `chosen` | picked this option when presented a choice. |
| `incidental` | let it happen: an agent's proposal, a provisional adoption, a stop-gap, anything merely committed or signed off. |

These are the only three. There is no proposed, trial, or ratified rung.
`intent` is required on every doc except references, which carry no intent.

### The evidence rule — `intent_basis`

`requested` and `chosen` require an `intent_basis`: the person's words quoted,
or a citation that locates them (session and date, review id, raw clipping
id). `ldoc` refuses to set either without one, and that refusal is the point —
the basis is what lets a later reader check the claim of authority instead of
trusting it.

The basis must show the person doing the act **for this claim**. None of these
is a basis:

- silence, or the person not contradicting a proposal;
- a commit, a merged change, or a review signature;
- the doc having a `provenance` edge (every new doc has one);
- an agent's generalization of something the person said, or a mechanism the
  person only saw in a report;
- the claim seeming important, or its type being `requirement`.

Judge per claim, not per batch: one request usually yields some claims the
person stated and some an agent articulated around them. Never stamp a batch
with one shared basis the source does not support for each claim.

`intent_basis` is shown by `ldoc get` and `ldoc show`, never in listings.

### Absent intent

A doc with no `intent` (legacy, not yet assessed) is shown as
**Unattributed** and is treated as `chosen` for the permission rule below
until someone assesses it. Nobody can yet tell an agent's suggestion from the
person's choice, and wrongly rewriting the person's choice costs more than
leaving an agent's suggestion alone for a while.

Assessing a doc means setting its `intent` from evidence: search its
provenance, history, and the raw clippings behind it for the person's act. If
the act is there, set `requested` or `chosen` with the basis; if it is not,
set `incidental`. Assessment changes the facet, never the claim. A legacy
`level` value is not evidence for intent — it measured something else; drop
it and assess.

## `force` — how hard the claim binds

| Value | Meaning |
|---|---|
| `must` | A rule. Deviation is a conflict. |
| `should` | A guideline. Deviation is allowed with a stated reason. |
| `may` | An allowance. |

Only normative types carry `force` (see `doc-types.md`). Force is independent
of intent: an `incidental` `must` is a rule an agent proposed; a `requested`
`should` is a guideline the person asked for. The line between a rule and a
guideline is often subtle and always matters, so choose it per claim from the
source's own words.

## What an agent may do — intent × force

Intent decides whether an agent may change the **doc**. Force decides whether
an agent may depart from the claim **in code or in another doc**.

| | May an agent change the doc's claim? |
|---|---|
| `requested`, `chosen`, Unattributed | **Never.** Record the agent's alternative as a new `incidental` doc, `relates` it to the doc it conflicts with, and flag the conflict to the person in the episode report. |
| `incidental` | **Yes, freely,** with a history note (`--note`) saying what changed and why. |

| | May an agent depart from the claim? |
|---|---|
| `must` | **Never without the person.** Stop and ask. |
| `should` | **Yes, with a stated reason** — in the change's note and the episode report. |
| `may` | Nothing to depart from; it grants an option. |

The two rules stack. On an `incidental` `must`, an agent may revise the doc
(the revision is visible in its history and the review) but may not let code
depart from a `must` the doc still states.

**The claim** is what the doc asserts and how it stands: its body claim,
title, type, `force`, `imposed_by`, `intent`, and `status` (deprecating a doc
alters it). An agent may update these on any living doc
without altering the claim: `realization` and its companions, the
`## Implementation` section, `provenance`, `relates`, and placement. A change
the person's own words direct — the request in an apply-to-docs episode, an
answer they gave — is the person altering the doc, with those words as the
basis.

**Severity when something conflicts with a doc.** A conflict with a `must` is
one only the person can resolve: cascade-check marks it `incompatible`, a
pre-write survey marks it `conflict-unresolved`. A conflict with a `should`
needs clarification: ask one targeted question (cascade-check's
`context-request`), unless the input already states the reason for departing
from it, which is then recorded with the change.

## `realization` — does the thing the doc claims exist in the implementation

| Value | Meaning |
|---|---|
| `realized` | It exists in the implementation. |
| `partial` | Some of it does. |
| `planned` | It does not exist yet, and it is wanted. |
| `deferred` | It is deliberately not being built now. |
| `unassessed` | Migrated or ingested material nobody has checked. |

The verb differs by type — a goal is "reached," a use-case "supported," a
requirement "met," a decision "in effect," a component "exists" (the table in
`doc-types.md`). Only realizable types carry `realization`; principles,
constraints, and guides exist whether or not any implementation follows them.

- **Realization is not status.** `status` says whether the doc is the current
  claim; `realization` says whether the implementation has caught up with it.
  A living decision that is not built yet is `living` and `planned`.
- **Assign it from the implementation, not from the source's tone.** "Done,"
  "shipped," and "all todos complete" record a mood at authoring time.
  Concepts recorded just before they are built in the current work are
  `planned`; concepts already built are `realized`; concepts the source
  explicitly puts off are `deferred`.
- **`planned` on a living doc is the build backlog**
  (`ldoc find --realization planned`). It is a claim that the work is wanted.
- **`deferred` never counts as drift.** The person decided not now; a deferred
  doc is not a gap to report or repair.
- **`unassessed` is only for migrated or ingested material.** An agent that
  just recorded a decision from its own session or a request can see whether
  the thing exists; `unassessed` there is skipping the check.
- **Companions.** `realization_refs` lists anchors — paths, symbols, URLs —
  where the implementation lives. `realization_verified` records the date or
  commit at which someone actually checked those anchors; set it only when you
  did.

**Implementation details are allowed.** People do want to record them; the
store gives them two places that keep them apart from the claim. Anchors go in
`realization_refs`. A description of how the claim is currently implemented
goes in a `## Implementation` section of the body. That section is volatile:
it is refreshed whenever realization is re-checked, it is exempt from the
rule that bodies state the why and not the what, and it is never a truth claim
— cascade, conflict detection, and the permission rule read the claim, not
this section.

## `imposed_by` — what makes this claim hold

| Value | The claim holds because… | Why-chain consequence |
|---|---|---|
| `environment` | the world imposes it: a regulation, a vendor, physics, a customer. | No upstream edge is needed; cite the source with `provenance`. |
| `tradeoff` | it follows from a choice recorded elsewhere in the store. | It **must** `requires` the decision or component it follows from. |
| `choice` | we set it directly. | It **should** `requires` the goal, use-case, or principle that motivates it. |

`imposed_by` is optional on every claim type and required on a constraint,
which takes any of the three values. The distinction is the one between a
technical constraint (`tradeoff`: it follows from a trade-off accepted
elsewhere), an organizational one (`choice`: a standard we set), and an
external one (`environment`).
The edges are what make the difference useful: when the choice a `tradeoff`
follows from changes, the `requires` edge is how cascade reaches the claim; a
`choice` with nothing above it states a rule with no reason a reader can
weigh. Missing edges are a gardening finding (`doc-types.md`, the why-chain).

## `status` — lifecycle only

| Value | Meaning |
|---|---|
| `living` | The current claim. |
| `deprecated` | Overturned; kept as history. Requires `superseded_by` and a `## Correction` section (the deprecation protocol in AGENTS.md). |
| `reference` | Frozen supporting material. |

Deprecated and reference docs are **frozen**: never rewritten to track new
state.

`target` is retired. What it used to carry now lives elsewhere: "decided, not
yet built" is `living` with `realization: planned`; "decided, put off" is
`living` with `realization: deferred`. **A current path and a desired path**
are both `living`: the doc for the current path carries `superseded_by`
pointing at its successor, which is `realization: planned`. When the
successor is realized, deprecate the current doc by the protocol — its
`superseded_by` is already in place. A legacy `status: target` maps the same
way: `living`, with realization set from the evidence.

## Orchestrator knobs (do not contradict this file)

- **apply-to-docs** — the request is the basis: a claim the person states in
  it is `requested` (quote it, citing the request's raw clipping); a claim an
  agent articulated around it is `incidental`. Concepts about to be built are
  `planned`; concepts the request puts off are `deferred`.
- **reconcile-changes** — docs are born `living` and, for what the session
  built, `realized` (with `realization_refs` where the anchors are known).
  Built and committed is evidence for realization, never for intent.
- **ingest-reference** — the material's author is not the person: a claim is
  `incidental` unless the material records the person requesting or choosing
  it. Realization comes from the material's evidence or a check; `unassessed`
  is allowed when neither settles it. Forces from outside are
  `imposed_by: environment`.
- **revise-doc** — the permission table gates what a revision may touch.
- **cascade-check** and **assess-blast-radius** — force sets conflict
  severity; the permission table decides whether a `cascade` write is allowed
  or the neighbor is flagged instead.
- **garden** — every phase obeys the permission table; assessing Unattributed
  docs is assessment, not a claim change.
