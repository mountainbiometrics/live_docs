---
name: identify-key-concepts
user-invocable: false
description: >
  Read an input — a request, a normalized reference, or a proposed doc revision
  — and emit a typed list of the durable concepts it asserts. Owns
  the single shared concept-extraction protocol: how to read an input and emit
  the Concept/Type/Asserts record shape. The type taxonomy it assigns from lives
  in _shared/doc-types.md. This is a phase sub-skill invoked by apply-to-docs,
  ingest-reference, and revise-doc; it is not meant to be run directly by a user.
---

# identify-key-concepts — Extract the typed concept list (shared phase)

This skill owns the **one** definition of concept extraction for the store — the
governed-write orchestrators invoke it rather than each re-implementing the
extraction protocol. It does exactly one thing: read an input and emit a typed concept list.
It writes nothing, queries no KB, and runs no `ldoc` commands. It says nothing
about what happens next — whoever invoked it still holds their own task and
resumes it once the list exists. (Mapping the list to existing docs is a separate
phase, `map-concepts-to-docs`.)

---

## Inputs

- **The text to scan** — the normalized restatement (apply-to-docs), the
  normalized reference (ingest-reference), or the proposed change (revise-doc).
- **Whether to apply the splitting test** — an opt-in refinement the calling
  flow may request (ingest-reference does; see Step 3). Nothing else is
  parameterized: always extract **every distinct durable concept** the input
  asserts — there is no target count — and label each record `Concept`.

---

## Step 1 — Scan by type

The type taxonomy — what each type means, and the "is this really a decision?"
ladder — lives in `.claude/skills/_shared/doc-types.md`. **Read and apply it**;
do not restate it here. Every concept you extract is typed from that file.

Scan the input as a **recognition pass**: for each type in the taxonomy, ask
"does the input assert an instance of this?", hunting top-down through the text
for each type in turn before moving on.

Extract concepts at the level of **durable claims**, not ephemeral
implementation steps. "We will add a field to the schema" is not a durable
concept; "edge metadata must include a weight field" is. Concepts are often
presupposed rather than stated outright — goals, principles, and requirements
may be implied by the text rather than asserted explicitly. If you find very
few, re-read through each type lens again.

### Root-over-decision (invariant)

Decisions and implementation choices are often recoverable later from code and
chat; the principles, constraints, requirements, and goals that justified them
usually are not. The store's job is that why-web — so a later challenge or
better alternative can be re-weighed against the same roots — not an inventory
of ADR-shaped outcomes.

When the input asserts (or clearly depends on) such a root claim *and* a
concrete choice that instantiates it, extract **both** as separate concepts:
the root typed `principle` | `constraint` | `requirement` | `goal`, and the
choice as a thinner `decision` | `component`. Do **not** collapse them into one
decision concept whose `Asserts` buries the root as rationale prose. A concept
list that is mostly `decision`s restating what was chosen, with the driving
reasons only implied inside those Asserts, has failed this step.

Do not invent a why-chain the input does not support. Implied roots are allowed
only when the text's choices are unintelligible without them.

---

## Step 2 — Record each concept

Write each concept found in the record shape below, labeled `Concept`:

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

## Step 3 — Splitting refinement (only when the calling flow asks for it)

When the calling flow requests the splitting test (ingest-reference does), apply
it to each concept already found: "This doc changes when ___." If that blank
covers more than one concern, split the concept into two before finishing. This
is a refinement tool, not a discovery lens — apply it only after the type-scan
above is complete, and only when the calling flow asks for it.

---

## Output

Emit the completed concept list under a `## Concept list` heading, in the record
shape from Step 2.
