---
name: ingest-reference
description: >
  Bring external material into the live_docs store without creating non-atomic
  blobs. Accepts a file path, pasted text, a chat-session summary, a URL's
  fetched content, or any other raw input. The skill creates a raw clipping doc,
  a normalized summary doc, then — the critical step — decomposes the material
  into single-responsibility docs (principles, decisions, constraints, etc.) or
  links it as supporting evidence to existing docs. Use whenever ingesting
  external knowledge: meeting notes, research, specs, prior-art findings,
  conversations, blog posts, RFCs, or any reference you want to make durable.
---

# ingest-reference — Bring external material into the store atomically

The cardinal rule: **the decomposition step is where atomicity is produced.**
A raw blob ingested as a single doc is a liability, not an asset. Do not skip
decomposition.

---

## Step 1 — Receive the material

Accept input in any of these forms:

- **File path**: read the file content.
- **Pasted text**: use as-is.
- **URL content**: use the fetched text (the caller is responsible for fetching;
  this skill works with the text only).
- **Chat session / conversation summary**: the caller pastes the summary.

Determine the `source` field value: URL, filename, meeting name/date, person,
or "pasted". If the source is ambiguous, ask before proceeding.

---

## Step 2 — Create the RAW reference doc (immutable clipping)

```bash
python3 scripts/ld.py ingest-raw \
  --from-file <path>           # OR: --body "<raw content>" OR: --body -
  --source "<where it came from>" \
  --title "Clipping: <descriptive title>"   # optional but recommended
```

This writes to the **raw/ tier** (repo root `/raw/<id>.md`), NOT to `docs/`.
`raw/` is outside the graph — `livedocs`, `validate`, and `reindex` scan only
`docs/` and will never load raw files.

- `raw/<RAW_ID>.md` is the **immutable archival original**.  Never edit its
  body after creation.
- If the content is large (> ~2000 words), you may truncate it in the raw file
  and note "full content at <source>" in the body — but prefer the full text.
- Note the created id printed to stdout: call it **RAW_ID**.

---

## Step 3 — Create the NORMALIZED reference doc

Read the raw content and produce a cleaned, summarized, lightly structured
version: remove cruft, organize into sections if helpful, extract the core ideas.

Determine `kind`:
- `plan` — if the material is a proposal, roadmap, or action plan.
- `brainstorm` — if it's exploratory, unresolved, or generative.
- `external` — if it's an external spec, RFC, article, or third-party source.
- `clipping` — only if none of the above fit.

```bash
python3 scripts/ld.py new \
  --type reference \
  --kind <kind> \
  --status living \
  --level incidental \
  --title "Reference: <descriptive title>" \
  --source "raw/<RAW_ID>.md" \
  --body "<normalized summary>"
```

Key differences from Step 2:

- This doc goes into **`docs/`** — it IS a graph node (NORM_ID lives in docs/).
- `--source "raw/<RAW_ID>.md"` is the provenance link to the raw tier.  Use a
  path, not a depends_on edge — raw files are not graph nodes, so a depends_on
  entry pointing at RAW_ID would be a dangling edge.
- Do NOT pass `--depends-on "<RAW_ID>"`.  RAW_ID is not in the graph.

Note the created id: call it **NORM_ID**.

---

## Step 4 — Decompose into atomic docs (THE KEY STEP)

Read the normalized reference and extract durable learnings. For each distinct
idea, ask: "Is this a single responsibility?" If yes, it becomes its own doc.

**Extraction categories** (pick the most precise type for each unit):

| What you find | Type to create |
|---------------|---------------|
| A design truth or rule that should guide future work | `principle` |
| A significant choice and its rationale | `decision` |
| An external force limiting options | `constraint` |
| A must-have behavior or property | `requirement` |
| A user story or workflow | `use-case` |
| A capability description | `component` |

For each extracted unit:

1. Draft a single-sentence summary: "This doc changes when X." If X covers more
   than one concern, split further.
2. Create with `ld new`:
   ```bash
   python3 scripts/ld.py new \
     --type <type> \
     --title "<precise, single-responsibility title>" \
     --level <incidental|trial|preference|requirement> \
     --state <actual|target> \
     --references "<NORM_ID>" \
     --tags-scope "<scope tags, e.g. live_docs,sinai>" \
     --body "<the extracted content>"
   ```
   The `--references NORM_ID` establishes provenance: this doc was extracted from /
   informed by that reference. This is the **provenance rule**.
   Use `--depends-on` for genuine structural dependencies (e.g. a decision that
   logically depends on a principle), added separately when they exist.
3. If the extracted idea DUPLICATES or STRENGTHENS an EXISTING doc: do not create
   a new doc. Instead, link NORM_ID to the existing doc's `references` list (not
   `depends_on`):
   ```bash
   python3 scripts/ld.py link <existing-id> --references <NORM_ID>
   ```

---

## Step 5 — Provenance rule check

After decomposition, every extracted doc MUST have at least one `references` entry
pointing to NORM_ID (or directly to the source if there's no normalized layer). A
floating extracted doc with neither `references` nor `source` nor `depends_on` is a
provenance violation — add the `references` edge.

---

## Step 6 — Report

After all docs are created, print a summary:

```
ingest-reference — complete
Source: <source description>
RAW_ID:  <id>   raw/<id>.md   — verbatim, immutable (NOT in graph)
NORM_ID: <id>   docs/<id>.md  — normalized reference (graph node)

Extracted docs:
  <id>  type: principle   title: "<title>"
  <id>  type: decision    title: "<title>"
  <id>  type: constraint  title: "<title>"

Linked to existing docs:
  <id>  "<existing doc title>" — added <NORM_ID> to depends_on

Next: consider running cascade-check if any existing docs were modified.
```

---

## Atomicity checklist before finishing

- [ ] Every extracted doc has exactly one responsibility (single-reason-to-change test).
- [ ] Every extracted doc has provenance: `references` includes NORM_ID (not RAW_ID — raw is not a graph node).
- [ ] `raw/<RAW_ID>.md` body is the verbatim, unedited original (raw tier, outside docs/).
- [ ] NORM_ID lives in `docs/` with `source: "raw/<RAW_ID>.md"` pointing back to the raw tier.
- [ ] NORM_ID body is a cleaned summary, not the extraction outputs.
- [ ] No extracted doc duplicates an existing doc (check by searching titles).
- [ ] No `depends_on` edge points at RAW_ID — raw files are not graph nodes.
