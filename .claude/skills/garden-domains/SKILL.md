---
name: garden-domains
user-invocable: false
description: >
  Gardening phase: curate the domain vocabulary as a finite shared resource —
  consolidate near-synonyms and underweight domains, assign untagged docs
  conservatively, validate claimed memberships, and normalize convention drift.
  Replaces the deprecated ≥2-scopes test. Nested phase; garden dispatcher owns
  the episode.
---

# garden-domains — Domain vocabulary curation (structure phase)

**Contract:** nested phase only. Capture no START, run no `cascade-check`, emit
no review.

**Read and apply** `.claude/skills/_shared/domain-tagging.md` — the shared
definition. Do not restate it here. Your phase-specific role is the **curator**:
the full-store, pruning half of the originate-liberally / prune-authoritatively
asymmetry. Origination tags liberally (isolated context, optimising for recall);
you have store-wide context, so consolidating and pruning the vocabulary is your
job, not the author's. `ldoc domains` is the live registry to curate against.

---

## The governing fear

**An un-pruned vocabulary is the failure mode this phase exists to prevent.**
Noisy, over-applied domains make the facet useless as a filter. Origination tags
*liberally* and is right to — it lacks store-wide context. **You have that
context, so pruning is your job, not the author's.** Prune and consolidate
eagerly; the safe error here is removing one tag too many, never leaving drift in
place. Every action must be answerable: "does this make the vocabulary more
justified, or just busier?"

---

## Procedure

### 1. Survey the registry

```bash
ldoc domains
```

This lists every distinct domain currently in use across the store, with the
count of docs carrying each. This is the shared vocabulary you are curating, not a
suggestion list — it is the live resource. If the store has zero domains, the
output is `domains — none in use`; when the registry is empty the phase's main
work is limited to step 4 (validate) and conservative step 3 (assign), applied
only where an obvious existing domain would apply.

### 2. Consolidate what doesn't pull its weight

**Fear:** leaving near-synonyms or singleton domains intact fragments the
vocabulary — neither copy carries its weight, and both pollute the filter.

Consolidation candidates:
- Near-synonyms (`acct_management` vs `Account Management`)
- A domain applied to only one doc — strong consolidation signal unless the
  domain is genuinely irreplaceable
- A domain indistinguishable in meaning from another

**Mechanic — a domain is not an object; it is a string on docs.**

To consolidate `A` → `B`:

```bash
# Find every doc carrying domain A
ldoc find --domain "A" --json

# For each such doc <id>:
ldoc show <id>          # read the full current domain list
# Swap A → B within the list, then re-set the whole list:
ldoc set <id> --domain "B,<other-domains-unchanged>"
ldoc history <id> --add "garden-domains: consolidated domain A→B"
```

`ldoc set --domain` has **replace semantics**: it replaces the doc's entire
domain list. Never pass only the new domain; always reconstruct the full list
with A swapped out and all other domains preserved. When the last doc stops using
A, A disappears from the registry automatically.

### 3. Assign untagged docs to existing domains — conservatively

**Fear:** inventing or speculatively applying domains inflates the vocabulary with
noise and defeats the finite-shared-resource discipline. The wrong direction is
invisible and accumulates.

Only assign a domain when:
- The doc clearly belongs to a domain already in the registry (prefer reuse over
  coining), AND
- You can state which concern the doc is about in that domain's terms, AND
- The domain would pull its weight with this doc included

If those conditions are not all met, leave the doc untagged. Under-proposing is
correct. Never coin a new domain to satisfy a single untagged doc.

```bash
ldoc set <id> --domain "<existing-domain>,<other-domains-if-any>"
ldoc history <id> --add "garden-domains: assigned to domain <name>"
```

### 4. Validate claimed memberships

**Fear:** a doc asserting a domain it is not actually about poisons the filter —
queries against that domain surface irrelevant results and erode trust in the
facet.

For each doc carrying a domain, confirm the doc is genuinely about that domain's
concern, not just adjacent to it or historically tagged. Remove inaccurate
memberships:

```bash
ldoc set <id> --domain "<corrected-list-without-erroneous-domain>"
ldoc history <id> --add "garden-domains: removed inaccurate domain <name>"
```

### 5. Normalize convention drift

**Fear:** inconsistent naming (`ui`, `UI`, `user-interface`) produces phantom
duplicate domains in the registry and breaks filtering — a user querying `ui`
misses `UI` docs.

The system is **not opinionated about which convention** is used (casing,
separators, singular vs plural) — only that whatever convention the store uses is
applied **consistently**. Identify the dominant form; normalize outliers to it.
Use the consolidate mechanic from step 2 (find docs carrying the variant, re-set
with the canonical form).

---

## What to leave alone

**Scope/domain value overlap is expected and fine.** Most docs in the `viewer`
scope sharing a `ui` domain is not noise — scope and domain are orthogonal axes
answering different questions (where a doc sits vs what concern it is about). Do
not "fix" overlap.

**Keywords that match a domain** are a refine/domains boundary note, not a
silent correction. If you spot a keyword duplicating a domain, flag it in the
output rather than silently removing it — that is a `garden-refine` concern.

---

## Output

```
garden — phase: domains
Scanned: N docs
Registry: [list of domains in use, or "none"]
Findings:
  …
Actions:
  …
Applied: [list]
Changed-ids: [id, …]
```
