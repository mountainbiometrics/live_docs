---
name: identify-key-concepts
user-invocable: false
description: >
  Read an input — a request, a normalized reference, or a proposed doc revision
  — and emit a typed list of the durable concepts (or claims) it asserts. Owns
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
- **The extraction count / label** — how many concepts to expect and what to
  call them. The calling flow sets this knob, e.g.:
  - apply-to-docs: "extract 3–10 concepts."
  - ingest-reference: "extract concepts, no upper limit; then apply the
    splitting test."
  - revise-doc: "extract 1–3 claims; label each record `Claim` not `Concept`."

  Honor the count and label the calling flow gives you. If none is given,
  default to extracting every distinct durable concept and labeling it
  `Concept`.

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

---

## Step 2 — Record each concept

Write each concept found in the record shape below. Use the label you were given
(`Concept` or `Claim`); the field shape is identical either way:

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

Emit the completed concept list, clearly labeled (e.g. `## Concept list` or
`## Claims`), in the record shape from Step 2.
