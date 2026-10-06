# Choosing a doc type — the shared definition

Single source of truth for every actor that assigns or re-assigns a doc's
`type` — the writer that types a doc at birth (ingest / apply /
`identify-key-concepts`) and the gardener that re-types it later — and for what
a type decides: which facets the doc carries and which `requires` edges it is
expected to have. Read and apply this; do not paraphrase from memory.

## The most common failure mode this prevents

**Almost anything can be rationalized as a "decision."** Every fact about the
system was, at some level, decided. If you reach for `decision` by default the
taxonomy collapses — which makes `decision` the largest and most misapplied
type. `decision` type should be used only for docs recording an "Architectural
Decision".

## The types and their intended use

| Type | Use it when the doc captures… | Not when… |
|---|---|---|
| `principle` | A **bedrock value or design truth** that guides *many* downstream choices; universal, not a single pick. | It's one specific choice → `decision`. |
| `decision` | A **deliberate architectural choice among alternatives**, with a rationale, that future work shouldn't re-decide — scoped to the level it binds. | It merely says a thing *exists* → `component`; it's *how to work* → `guide`; it's *imposed, not set directly* → `constraint`. |
| `constraint` | A **force that limits options** that we did not set directly — imposed by the world, or following from a choice recorded elsewhere — that the system must work *within*. | We set it directly → `decision` or `requirement`. |
| `requirement` | A **must-have property or behavior** the system has to satisfy. | It's the *choice of how* to satisfy it → `decision`. |
| `use-case` | A **user story, workflow, or deployment scenario** the system serves. | It's a capability that serves the scenario → `component`. |
| `goal` | A **desired end-state or outcome** the system is trying to reach. | It's a fixed property that must always hold → `requirement`. |
| `component` | A **thing that exists in the system** — a capability, module, subsystem, boundary, or contract. | It's a *choice about* the thing rather than the thing → `decision`. |
| `guide` | **How to do or think about** something when working with the system — a how-to, procedure framing, or orientation. | It records a design choice the system embodies → `decision`. |
| `reference` | **Frozen source material** — clippings, brainstorms, external docs, session digests. Never a truth-claim. | It's a distilled claim *extracted from* the source → its proper type above. |
| `type` | The **definition of a type itself** (meta / self-defining). Rare. | — |

## The typing test

Two properties of a claim decide most types, and `facets.md` defines both:
**realizable** (the implementation can have it or lack it — it carries
`realization`) and **normative** (it tells what must or should hold — it
carries `force`).

- First, is it a **purpose** — an outcome to reach (`goal`) or a scenario to
  support (`use-case`)? Purposes are realizable and not normative.
- Realizable + normative + a choice among alternatives → **`decision`**.
- Realizable + normative, not a choice (a property that must hold however we
  achieve it) → **`requirement`**.
- Realizable, not normative → **`component`**.
- Normative, not realizable → **`principle`**, or **`constraint`** when it is
  imposed from outside. How to work with the system, rather than a claim about
  it → **`guide`**.

A constraint is a requirement imposed from outside that binds as `must`; the
type is kept because it is the word people use for that.

## The "is this really a decision?" ladder

Before typing anything `decision`, walk these in order and stop at the first yes:

1. Does it just say **a thing exists**, or describe a module / boundary /
   contract? → **`component`**. ("Have a module that does X" is a component
   named "module for X", not a decision.)
2. Does it tell an actor **how to work** with the system (classify, place,
   run a workflow)? → **`guide`**.
3. Is it a force the system must live **within**, that we did not set
   directly (an upstream limit, a platform rule, a physical/legal bound, or a
   consequence of a trade-off recorded elsewhere)? → **`constraint`**.
4. Is it a property that **must hold**, independent of how we achieve it? →
   **`requirement`** (or **`goal`** if it's an outcome we're moving toward).
5. Is it a **universal value** guiding many choices, not a single pick? →
   **`principle`**.
6. Only if none of the above: is it a **specific choice among real
   alternatives, with a rationale**, that should not be re-litigated? →
   **`decision`** — and then scope it (see below).

Prefer `decision` over `principle` when you're typing **one** claim about how
the system behaves (a behavioral choice); reserve `principle` for bedrock
values. That preference is a *typing* rule for a single claim — it is not
permission to skip extracting separable root principles/constraints/
requirements/goals when the input also carries a concrete choice. When both
are present, extract both (see identify-key-concepts's root-over-decision
invariant): the why-roots are the prize; the decision is the thin modeling
node.

## Two rules that apply to a `decision` once you've confirmed it

- **Architectural, not existential.** A real decision records the *alternatives*
  and *why* this one won — not merely the outcome. It should be **excisable**:
  swapping the choice (a library, a format) should be a one-atomic-doc change. A
  "decision" you can't restate as "X over Y because Z" is probably a
  `component`.
- **Scoped to the level it binds.** Place it via `belongs_to` under the subtree
  it governs, so it constrains that subtree and not its siblings. A decision with
  no `belongs_to` is **global** — which is legitimate for genuinely cross-cutting
  architectural choices, but wrong for one that should bind only a single
  project/subsystem. (See the placement shared definition for what the hierarchy
  means.)

## Facets and expected edges per type

The one table of which facets each type carries and which `requires` edges it
is expected to have. What each facet value means is `facets.md`. **Required**
facets must be set on every doc a tool writes (on an existing doc a missing one
is a warning); **forbidden** facets are an error if present; **optional** ones
may be set when they are known. `intent` is required on every type except
`reference`.

| Type | `force` | `realization` (verb) | `imposed_by` | Expected `requires` |
|---|---|---|---|---|
| `goal` | forbidden | required ("reached") | optional | none |
| `use-case` | forbidden | required ("supported") | optional | a goal |
| `principle` | required | forbidden | optional | a goal or use-case |
| `constraint` | required | forbidden | required: `environment` or `tradeoff` | a decision or component, when `tradeoff` |
| `requirement` | required | required ("met") | optional | a goal or use-case |
| `decision` | required | required ("in effect") | optional | a principle, constraint, or requirement |
| `component` | forbidden | required ("exists") | optional | a decision or requirement |
| `guide` | required | forbidden | optional | a principle or decision |
| `reference` | forbidden | forbidden | forbidden | none; no `intent` either |
| `type` | forbidden | forbidden | optional | none |

There is no `tier` field: which layer of the why-chain a doc sits on is a
property of its type, read from this table.

## The why-chain

The expected `requires` edges form one chain, read bottom-up: **shapes require
norms, norms require purposes, purposes require nothing.** Decisions and
components (shapes) require the principles, constraints, and requirements
(norms) they serve; norms require the goals and use-cases (purposes) that
motivate them. The chain is what lets a later reader re-weigh a shape against
the reason for it, and what lets cascade reach a shape when its reason changes.

**A norm with no goal or use-case above it is the loudest gardening signal**:
it is a rule nobody can weigh, because the purpose it serves was never
written down. Goals and use-cases are the types this store under-records most;
when extraction finds a norm, look for the purpose behind it. Do not invent
one — a purpose the source does not state is a question for the person.
`imposed_by` adds its own edge expectations (`facets.md`).

## Cross-cutting: every doc carries its why

Regardless of type, a non-signpost doc must carry its *why* (the rationale,
constraint, use-case, or decision it serves). A doc that states only a *what*,
with no why, is repaired or removed — docs capture the *why*, not the *what* the
code already encodes. The why is carried twice: in the body, and as the
`requires` edges of the why-chain above. Signposts (docs that exist to group
their children) are the one exception. A body's `## Implementation` section is
exempt from this rule (`facets.md`, realization).
