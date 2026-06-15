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

1. List all docs and load each one:
   ```bash
   python3 scripts/ld.py ls --json          # full id list
   python3 scripts/ld.py show <id>          # title, type, edges, history, body
   ```
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
   - Create each new doc:
     ```bash
     python3 scripts/ld.py new --type <type> --title "<title>" \
       --level <level> --state <state> --depends-on <dep-ids>
     ```
   - Retire the original doc:
     ```bash
     python3 scripts/ld.py set <original-id> --status historical
     python3 scripts/ld.py history <original-id> --add "split into <A-id> and <B-id>"
     ```
   - Update any docs that pointed to the original and now should point to A or B:
     ```bash
     python3 scripts/ld.py unlink <pointing-doc> --depends-on <original-id>
     python3 scripts/ld.py link   <pointing-doc> --depends-on <A-id>
     python3 scripts/ld.py history <pointing-doc> --add "rewired depends_on from <original-id> to <A-id> after split"
     ```
5. After splits, run `cascade-check` on each new doc to confirm consistency.

**Hot-file heuristic**: sort docs by history length descending — `ld get <id>
--json` includes the `history` array; count entries. Docs in the top 10% with
> 3 history entries AND mixed-topic summaries are prime candidates.

---

### Pass 2: `staleness`

**Goal**: find docs whose dependencies were updated more recently than the doc
itself — potential stale dependents.

1. For each doc D, load its history and note the most recent `at` timestamp:
   ```bash
   python3 scripts/ld.py get <id> --json   # includes history array
   ```
2. For each id in D's `depends_on` (from `ld neighbors <id> --kind depends_on
   --json`), load the dependency's history and note its most recent `at`
   timestamp.
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

Start with an automated scan:
```bash
python3 scripts/ld.py validate
```
This surfaces broken `depends_on` references and missing/invalid fields.
Then complement with graph-level checks:

1. **Broken depends_on references**: flagged by `ld validate`. For each broken
   ref, propose removing or correcting via `ld unlink <id> --depends-on <bad-id>`.
2. **Orphans**: docs with no outbound AND no inbound edges. Find them:
   ```bash
   python3 scripts/ld.py edges --json   # inspect docs with empty forward+reverse
   ```
   Or read `docs/.index/orphans.txt` (from the last reindex). Exempt `type: index`
   and `type: type` docs. For genuine orphans, propose: add edges via `ld link`
   or retire with `ld set <id> --status historical`.
3. **Missing required fields**: surfaced by `ld validate`. Propose the missing
   field's value; apply with `ld set <id> --<field> <value>`.
4. **id != filename**: surfaced by `ld validate`. Propose correcting the
   frontmatter (do NOT rename the file); apply with `ld set <id> --...` or direct
   frontmatter edit.

Present all proposals together. On user confirmation, apply them, recording history
entries with `ld history <id> --add "..."` for each modified doc.

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
1. List all docs via `ld ls --json`. For each, load frontmatter with `ld get <id>
   --json` and scan for keys matching a `field_aliases` entry or values matching
   `value_aliases`. Rename/replace as needed via direct frontmatter edit (no `ld`
   verb exists for arbitrary key rename).
2. For canonical-field enum corrections (e.g. `status`, `level`, `state`), use:
   ```bash
   python3 scripts/ld.py set <id> --status living   # example
   ```
3. Changes are applied **non-destructively**: record a history entry noting the
   normalization:
   ```bash
   python3 scripts/ld.py history <id> --add "field-aliases normalization: renamed <old> → <new>"
   ```
   Do not change any semantic content.
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
