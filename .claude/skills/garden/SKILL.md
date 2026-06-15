---
name: garden
description: >
  Periodic maintenance pass that enforces Single Responsibility, catches drift,
  repairs orphans, and normalizes schema. The PRIME DIRECTIVE is decomposition:
  find docs carrying more than one responsibility and propose concrete splits.
  Use this when the store feels cluttered, after a wide cascade warning, when
  a doc has many history entries and seems to be a "hot file", or on a regular
  schedule (e.g. weekly). Each pass can be run alone or combined.
---

# garden — Decomposition and drift engine

The foundational test for every pass: **"Can this doc change for more than one
reason?"** If yes, it violates Single Responsibility and is a split candidate.

Gardening **proposes** and (with user confirmation) **applies** decompositions.
It never silently rewrites meaning, deletes docs, or merges distinct ideas.

---

## Passes

Run one pass by naming it, or run all with `garden all`. Each pass is
independent; run them in any order.

---

### Pass 1: `single-responsibility` (the headline pass)

**Goal**: find docs bundling multiple responsibilities and propose concrete splits.

1. Scan every `docs/<id>.md`. For each doc, read title, type, body, and history.
2. Ask: "Can this doc change for more than one reason?" Signals that a doc is a
   split candidate:
   - Body has multiple `##` sections that address distinct concerns (not just
     sub-sections of one concern).
   - The `history` list has many entries with varied summaries (hot-file signal:
     many parties update this doc for different reasons).
   - The `depends_on` list is very long (pulling in many unrelated inputs).
   - The doc's title uses "and" or contains a list ("X and Y", "A, B, C").
   - You would naturally say "this doc owns X, but it also owns Y."
3. For each split candidate, PROPOSE (do not auto-apply without confirmation):
   - **New doc A**: what it owns, suggested title and type.
   - **New doc B**: what it owns, suggested title and type.
   - How `depends_on` edges would be rewired (which existing docs would now point
     to A or B instead of the original; the original may become an index or be
     retired to `status: historical`).
   - The `depends_on` of A and B (provenance: they likely both depend on whatever
     the original depended on, unless that too should be split).
4. Present the full proposal to the user. On confirmation:
   - Create each new doc with `python scripts/new_doc.py` using the appropriate
     type, title, level, state, and `--depends-on`.
   - Update the original doc: set `status: historical`, add a history entry
     citing the new doc ids. Do NOT delete it.
   - Update any docs that pointed to the original and now should point to A or B:
     edit their `depends_on` fields and add a history entry.
5. After splits, run `cascade-check` on each new doc to confirm consistency.

**Hot-file heuristic**: sort docs by `len(history)` descending. Docs in the top
10% with > 3 history entries AND mixed-topic summaries are prime candidates.

---

### Pass 2: `staleness`

**Goal**: find docs whose dependencies were updated more recently than the doc
itself — potential stale dependents.

1. For each doc D, note its most recent history `at` timestamp.
2. For each id in D's `depends_on`, note that dependency's most recent history
   `at` timestamp.
3. If any dependency was updated AFTER D's last update, D is a **staleness flag**.
4. Emit a report:
   ```
   Staleness candidates:
   <id>  "<title>"  — dependency <dep-id> updated <dep-date>, this doc last updated <doc-date>
   ```
5. For each flagged doc, suggest: "Run cascade-check with changed doc = <dep-id>
   to evaluate whether <id> needs updating."
6. Do not auto-update. Surface only; let the user decide which to investigate.

---

### Pass 3: `consistency`

**Goal**: structural integrity — orphans, broken edges, missing required fields.
(Overlaps `validate` but garden PROPOSES fixes rather than just reporting.)

1. **Broken depends_on references**: for each doc, check every id in `depends_on`
   resolves to an existing `docs/<id>.md`. Report broken refs and propose removing
   or correcting them.
2. **Orphans**: docs with no outbound (`depends_on`) AND no inbound (nothing lists
   them in `depends_on`) edges. Exempt root index/type docs (they are by design
   anchors). For genuine orphans, propose: add edges or retire to `historical`.
3. **Missing required fields**: any doc missing `id`, `title`, `type`, `status`,
   `level`, `state`, `depends_on`, `tags`, `created`, or `history`. Propose the
   missing field's value.
4. **id != filename**: if frontmatter `id` doesn't match the filename (without
   `.md`), flag it. Propose correcting the frontmatter (do NOT rename the file).

Present all proposals together. On user confirmation, apply them, adding history
entries to each modified doc.

---

### Pass 4: `field-aliases`

**Goal**: normalize frontmatter schema drift over time without rewriting meaning.

Uses a versioned alias map: a mapping of old field names (or old enum values) to
their current canonical equivalents. The map is stored (or can be stored) as a
small JSON or markdown table in this skill directory, e.g. `field-aliases.json`.

Default alias map (extend as the schema evolves):

```json
{
  "field_aliases": {
    "depends": "depends_on",
    "depend_on": "depends_on",
    "tag": "tags",
    "created_at": "created"
  },
  "value_aliases": {
    "status": { "archived": "historical", "active": "living" },
    "level": { "none": "incidental", "required": "requirement" },
    "state": { "current": "actual", "desired": "target" }
  }
}
```

Procedure:
1. For each doc, scan frontmatter for any key matching a `field_aliases` entry.
   Rename the key to the canonical name.
2. For each canonical field with an enum, scan its value against `value_aliases`.
   Replace non-canonical values with canonical ones.
3. Changes are applied **non-destructively**: add a history entry noting the
   normalization; do not change any semantic content.
4. Report how many docs were normalized and which fields were affected.

---

## Output format

For each pass, emit:

```
garden — pass: <pass-name>
Scanned: N docs
Findings:
  <id>  "<title>"  — <finding description>
  ...
Proposals:
  [1] <concrete action>
  [2] <concrete action>
  ...
Awaiting confirmation to apply. Type "apply [1,2,...]" or "apply all" or "skip".
```

After applying, print:
```
Applied: [list of actions taken]
Docs modified: [list of ids]
```
