# Label, title, summary — the three descriptors

Single source of truth for naming a doc. Every actor that creates or renames a
doc reads and applies this. The three descriptors are NOT interchangeable; each
has one job (see decision `20260615230659`). All three follow `doc-style.md`'s
plain-register rule: established terms, literal statements, no metaphor — the
summary especially, since it is quoted verbatim wherever the doc is surfaced.

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
- **Say what the reader would learn about by opening the doc — don't be a
  label of the answer.** A label names the topic or tension the doc resolves,
  not the resolved conclusion stated as a claim. `Retry Backoff` names the
  topic (you'd learn about how retries back off); `Retries Wait Exponentially
  Longer Between Attempts` states the answer outright and reads as a fragment
  pulled from the doc's body, not a handle for it. The same goes for slogan
  and imperative labels — `Derive Nothing`, `Duplicate Over Share`, `Unset
  Binds The Author` are compressed verdicts, not handles; name the topic
  instead: `Stated Premise`, `Case Duplication`, `Unset Values`.
- **Ban meta-jargon suffixes** that name the store's own machinery rather than
  the domain — "Primitive," "Pattern," "Mechanism," a bare "Model." `Retry
  Backoff Mechanism` tells a reader nothing `Retry Backoff` didn't already.
- **Prefer the source's vocabulary.** When the material (request, digest,
  reference) already names the thing in the user's or project's words, those
  words win over an agent-coined Title-Case handle. A coined label that does
  not appear in the source is a proposal, not established usage — especially
  when the user rejected one term and supplied another.
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
  fragment — in working-title register: the line an engineer would type, not
  the body's thesis compressed into a carved sentence (see `doc-style.md`'s
  plain-register rule). `Evaluate at capability grain` — yes; `A
  capability's competence is measured at its own grain, with no pipeline
  awareness and no whole schema` — that is the body's opening claim doing
  double duty as a name.

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
