# Label, title, summary — the three descriptors

Single source of truth for naming a doc. Every actor that creates or renames a
doc reads and applies this. The three descriptors are NOT interchangeable; each
has one job (see decision `20260615230659`).

## `label` — REQUIRED, the primary handle

A short **2–5 word Title-Case** name that says *what the doc is about*. It is the
human-and-agent handle used to reference the doc in commands, prose, and review
output, and the compact name shown in displays.

- **Always provide `--label` on `ldoc new`.** There is no auto-derivation; an
  omitted label is an error, by design.
- **It must name the subject, not be a fragment.** `Singular Ownership`,
  `Domain Registry`, `Cascade Engine` — yes. `The Domain Vocabulary Is`,
  `State Policy Is`, `Ddl Entities Are` — no: these are truncations that tell a
  reader nothing. If your label reads like the first few words of a sentence, it
  is wrong; rewrite it as a noun phrase naming the thing.
- Title-Case, unique across the store (case-insensitive), letters/digits with
  single spaces or hyphens. Quote multi-word labels on the CLI.

## `title` — OPTIONAL, an elaboration of the label

A fuller, sentence-length descriptive name. It **defaults to the label** when
omitted, so only provide `--title` when you have something more informative to
say than the label already does.

- Provide a title when the full claim adds real information beyond the handle —
  e.g. label `Singular Ownership`, title `Singular ownership is the ownership
  face of single responsibility`.
- If the title would just restate the label, omit it and let it fall back.
- A provided title should be a complete, informative statement — not itself a
  fragment.

## `summary` — the signpost

A **tight 1–3 sentence** overview (≤ ~50 words) held in frontmatter. It is the
single source for overview snapshots in review output, CLI display, and
navigation. Name what the doc establishes and why a reader would open it; do not
run on, and do not just copy the body's first line.

## At creation

```bash
ldoc new --type <type> --label "<2–5 word handle>" [--title "<fuller statement>"] \
  --summary "<1–3 tight sentences>" ...
```

Label is mandatory and meaningful; title is optional elaboration; summary is the
signpost. Getting the label right at birth is cheaper than a gardening pass to
fix a lazy one later.
