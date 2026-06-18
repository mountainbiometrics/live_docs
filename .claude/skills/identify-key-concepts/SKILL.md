---
name: identify-key-concepts
user-invocable: false
description: >
  Read an input — a request, a normalized reference, or a proposed doc revision
  — and emit a typed list of the durable concepts (or claims) it asserts. Owns
  the single shared concept-extraction protocol: the principle/decision/
  constraint/requirement/use-case/component taxonomy, the "prefer decision over
  principle when describing HOW the system behaves" rule, and the
  Concept/Type/Asserts record shape. This is a phase sub-skill invoked by
  apply-to-docs, ingest-reference, and revise-doc; it is not meant to be run
  directly by a user.
---

# identify-key-concepts — Extract the typed concept list (shared phase)

This skill owns the **one** definition of concept extraction for the whole
store. The three governed-write orchestrators (`apply-to-docs`,
`ingest-reference`, `revise-doc`) each invoke it instead of re-implementing the
taxonomy. It reads an input and produces nothing but a typed list — no `ldoc`
commands, no KB queries. Mapping that list to existing docs is a separate phase
(`map-concepts-to-docs`).

---

## Nested-invocation rule (read first)

This skill is **always a nested invocation** — it is called by an orchestrator
that owns the episode. It therefore:

- does NOT capture a `START` time,
- does NOT run `ldoc review new` or emit any review summary,
- does NOT re-invoke the calling orchestrator or any other write skill.

It leaves its output in context as a clearly-labeled concept list for the
orchestrator to read. The orchestrator emits the single review summary for the
episode.

---

## Inputs (supplied by the orchestrator)

- **The text to scan** — the normalized restatement (apply-to-docs), the
  normalized reference (ingest-reference), or the proposed change (revise-doc).
- **The extraction count / label** — how many concepts to expect and what to
  call them. The orchestrator passes this as a knob, e.g.:
  - apply-to-docs: "extract 3–10 concepts."
  - ingest-reference: "extract concepts, no upper limit; then apply the
    splitting test."
  - revise-doc: "extract 1–3 claims; label each record `Claim` not `Concept`."

  Honor the count and label the orchestrator gives you. If none is given,
  default to extracting every distinct durable concept and labeling it
  `Concept`.

---

## Step 1 — Scan by type

Use the table below as a recognition checklist. For each category, ask: "Does
the input contain an instance of this?" Hunt top-down through the text for each
type in turn before moving on.

| What you find | Type |
|---|---|
| A design truth or rule that should guide future work | `principle` |
| A significant choice with a rationale | `decision` |
| An external force limiting options | `constraint` |
| A must-have behavior or property | `requirement` |
| A user story or workflow | `use-case` |
| A system capability or component | `component` |

**Prefer `decision` over `principle` when the input describes HOW the system
should behave** — a behavioral choice among alternatives with a rationale.
Principles are universal guidelines; decisions are specific choices.

Extract concepts at the level of **durable claims**, not ephemeral
implementation steps. "We will add a field to the schema" is not a durable
concept; "edge metadata must include a weight field" is. Concepts are often
presupposed rather than stated outright — goals, principles, and requirements
may be implied by the text rather than asserted explicitly. If you find very
few, re-read through each type lens again.

---

## Step 2 — Record each concept

Write each concept found in the record shape below. Use the label the
orchestrator gave you (`Concept` or `Claim`); the field shape is identical
either way:

```
Concept: "<short noun phrase>"
  Type:    <principle | decision | constraint | requirement | use-case | component>
  Asserts: <one sentence: the single claim this concept makes about how things should be>
```

Each concept should be expressible as a short noun phrase. Commit each
`Asserts` sentence before finishing: a precise claim produces exact KB matches
or confident misses in the next phase; a vague phrase produces weak matches
that get wrongly accepted.

---

## Step 3 — Splitting refinement (only when the orchestrator asks for it)

When the orchestrator requests the splitting test (ingest-reference does), apply
it to each concept already found: "This doc changes when ___." If that blank
covers more than one concern, split the concept into two before finishing. This
is a refinement tool, not a discovery lens — apply it only after the type-scan
above is complete, and only when the calling orchestrator asks for it.

---

## Output

Leave the completed concept list in context, clearly labeled (e.g.
`## Concept list` or `## Claims`), for the orchestrator to read and pass to
`map-concepts-to-docs`. Do not query the KB, write any doc, or emit a review
summary — those belong to later phases owned by the orchestrator.
