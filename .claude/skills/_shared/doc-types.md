# Choosing a doc type — the shared definition

Single source of truth for every actor that assigns or re-assigns a doc's
`type` — the writer that types a doc at birth (ingest / apply /
`identify-key-concepts`) and the gardener that re-types it later. Read and apply
this; do not paraphrase from memory.

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
| `decision` | A **deliberate architectural choice among alternatives**, with a rationale, that future work shouldn't re-decide — scoped to the level it binds. | It merely says a thing *exists* → `component`; it's *how to work* → `guide`; it's *given, not chosen* → `constraint`. |
| `constraint` | An **external force that limits options** — something the system must work *within*, that we did not choose. | We chose it → `decision`. |
| `requirement` | A **must-have property or behavior** the system has to satisfy. | It's the *choice of how* to satisfy it → `decision`. |
| `use-case` | A **user story, workflow, or deployment scenario** the system serves. | It's a capability that serves the scenario → `component`. |
| `goal` | A **desired end-state or outcome** the system is trying to reach. | It's a fixed property that must always hold → `requirement`. |
| `component` | A **thing that exists in the system** — a capability, module, subsystem, boundary, or contract. | It's a *choice about* the thing rather than the thing → `decision`. |
| `guide` | **How to do or think about** something when working with the system — a how-to, procedure framing, or orientation. | It records a design choice the system embodies → `decision`. |
| `reference` | **Frozen source material** — clippings, brainstorms, external docs, session digests. Never a truth-claim. | It's a distilled claim *extracted from* the source → its proper type above. |
| `type` | The **definition of a type itself** (meta / self-defining). Rare. | — |

## The "is this really a decision?" ladder

Before typing anything `decision`, walk these in order and stop at the first yes:

1. Does it just say **a thing exists**, or describe a module / boundary /
   contract? → **`component`**. ("Have a module that does X" is a component
   named "module for X", not a decision.)
2. Does it tell an actor **how to work** with the system (classify, place,
   run a workflow)? → **`guide`**.
3. Is it a force the system must live **within**, that we did not choose
   (an upstream limit, a platform rule, a physical/legal bound)? → **`constraint`**.
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

## Cross-cutting: every doc carries its why

Regardless of type, a non-signpost doc must carry its *why* (the rationale,
constraint, use-case, or decision it serves). A doc that states only a *what*,
with no why, is repaired or removed — docs capture the *why*, not the *what* the
code already encodes. Signposts (docs that exist to group their children) are the
one exception.
