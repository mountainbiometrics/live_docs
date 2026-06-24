# Domain tagging — the shared definition

Single source of truth for every actor that applies or curates `domain` tags —
the writer that originates tags at doc birth and the gardener that curates the
vocabulary later. Read and apply this; do not paraphrase from memory. Your
*role* differs by context (see "Two roles" below), but the *definition* here is
the same for both.

## What a domain is

- A `domain` groups a doc by the **business/problem concern it is about** —
  independent of where the doc sits (`scope`) and of which repo/service it
  pertains to. It is the **governed, filterable grouping facet**.
- The set of domains in use is a **finite shared resource**: each domain must
  **justify its own existence** — pull its weight as a distinct grouping a reader
  would filter by. Not a scope-count; weight (see `20260624185845`).
- `domain` is **not** `keywords`. Keywords are ungoverned search aliases; domain
  is the governed facet. The two **must not overlap**: a term that is or matches
  an existing domain belongs as a `domain`, not a keyword (`20260623233935`).
- Scope/domain *value* overlap is **expected and fine** — most `viewer`-scope
  docs sharing a `ui` domain is not noise; the axes answer different questions.

## The registry — reuse over coin

`ldoc domains` lists every domain currently in use, with doc counts. It is the
shared vocabulary. Whenever you apply a domain, **prefer reusing an existing
domain string over coining a new synonym** — this curbs drift at the source.
Coin a new domain only when nothing existing fits.

## Two roles (the bias is asymmetric)

Origination and curation happen in different contexts and carry **opposite**
biases (`20260624185902`):

- **Originating (isolated context — you hold only this doc's concepts):** tag
  **liberally**. Apply every domain that plausibly applies; optimize for recall.
  You cannot see whether a domain pulls its weight store-wide, so do not guess
  conservatively — over-tagging at birth is expected and harmless. Still reuse
  over coin.
- **Curating (full-store context — you hold the whole vocabulary):** prune
  **authoritatively**. You alone have the standing to judge weight: consolidate
  synonyms, remove tags that don't justify themselves, normalize convention. This
  is where the finite-shared-resource discipline is enforced.

Apply the role that matches your context. The shared bias across both: reuse an
existing domain over inventing one.
