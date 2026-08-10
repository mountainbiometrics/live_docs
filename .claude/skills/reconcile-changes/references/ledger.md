# Ledger — reconcile-changes

Edit history for skill refinements. Newest first.

## 2026-08-04 — Point born-living knob at shared status definition (Class B)

**Failure:** Sibling skills over-used `status: target`; reconcile already
defaulted born-`living` but body-content still said "unbuilt → target" without
the shared deferral horizon.

**Class:** B (suite-wide) — tighten exception language to
`_shared/status-living-vs-target.md`.

**Diff:** Born-living knob + body-content + checklist cite the shared file;
exception remains decided-but-explicitly-unbuilt under that test.

**Regression answers:**
1. Born-living, no pause — yes; strengthened by shared deferral test.
2–7. Why-priority / dedup / digest / review / validate / root-over-decision — yes.

---

## 2026-07-23 — Disambiguate why-priority + batch self-check (Class B + A)

**Failure:** Despite existing "abstract/why" bias, reconcile produced
decision-inventory first passes; close/review did not surface type-mix / naming /
level smells.

**Class:** B for Step 2 prompt ("rationale/why behind each decision"); A for
close self-check.

**Diff:** Rewrote priority blurb and Step 2 extraction prompt to mandate
root-over-decision (thin decisions, separate root concepts). Added pre-close
batch self-check (type-mix, labels, levels, source string). Updated checklist.

**Regression answers:**
1. Born-living, no pause — unchanged.
2. Abstract/why priority — yes, strengthened to root-over-decision shape.
3. Heavy dedup — unchanged.
4. Optional digest provenance — unchanged.
5. One episode review — unchanged.
6. Validate, no reindex — unchanged.

---

## 2026-08-10 — Make the write phase unskippable; widen the code-mirroring test (Class B ×2 + Class A)

**Failure:** An agent ran `/reconcile-changes` end to end and wrote 14 docs
directly with `ldoc new`. Result: every doc tagged `domain:
ground-truth-evaluation` when the concern lived inside one subsystem (a `scope`
mis-tagged); labels that state conclusions ("Presence Is The Ceiling", "Carried
Is Not Consulted", "Worth Is What Is Lost"); two bodies each carrying two
concepts; 8 of 14 restating implementation the code already holds; and a
reported "heavy dedup" that created 14 docs and revised 2. The store validated
clean throughout. User reports this is the same feedback they give every agent
on its first ldoc writes.

**Evidence (first-hand, from the failing run):** the agent read
`session-lifecycle.md`, `status-living-vs-target.md`, and `doc-types.md`;
invoked `identify-key-concepts` and `cascade-check`; and performed
`map-concepts-to-docs`, `assess-blast-radius`, and `synthesize-doc-changes`
inline instead of invoking them. It therefore never read
`label-title-summary.md`, `domain-tagging.md`, `doc-style.md`, or
`belongs-to-placement.md` — all four are referenced from
`synthesize-doc-changes` and from nowhere else in the pipeline.

**Class:**
- **B** — Step 5 read as "do this yourself". Steps 2–4 all say *"Run — but do
  not stop after — /skill"*; Step 5 said *"Run /synthesize-doc-changes, handing
  it:"* and closed with *"(This phase runs inline — it needs the whole impact
  set in view.)"*. Against the Step 2–4 cadence that parenthetical reads as a
  contrast: this one, unlike the others, is performed rather than delegated.
- **B** — Step 2's code-mirroring prohibition was scoped to `component`-type
  concepts only ("Do NOT stop at `component`-type concepts that merely mirror
  what the code now does"). The offending docs were `constraint`s and
  `requirement`s, so they passed a rule that never named their type.
- **A** — the scope-first test ("a concern inside one subsystem is captured by
  its `scope`; use `domain` only across two or more") lives in
  `reference/SKILL.md` §4 and was absent from `_shared/domain-tagging.md`, whose
  origination guidance says only "tag liberally".

**Diff:**
- `reconcile-changes` Step 5: verb aligned to the Step 2–4 cadence; the
  contrastive parenthetical replaced with a plain statement of ordering plus an
  explicit "do not write with raw `ldoc new`/`set` in its place", naming the
  four shared files reachable only there and why nothing downstream catches it.
- `reconcile-changes` Step 2 knob: code-mirroring prohibition widened from
  `component`-type to any type, with the operative test made explicit — "would
  this still be knowable if the implementation were rewritten?"
- `reconcile-changes` Step 8 self-check: `Labels` split into two tests
  (vocabulary, already present; shape, new — a label that states the conclusion
  is wrong even when every word came from the session). New `Domain vs scope`
  bullet for the batch-shares-one-subsystem-domain tell.
- `_shared/domain-tagging.md`: added the scope-first bullet, worded so the
  liberal-origination bias still applies within genuinely cross-scope concerns.
- `apply-to-docs` Step 6 and `ingest-reference` Step 5b: same one-sentence
  do-not-substitute guard. Deliberate extrapolation — the mechanism is not
  reconcile-specific and the user reports the failure is universal to first-time
  agents. `revise-doc` already carried an equivalent guard (line ~139).

**Regression answers (all 8 anchors):**
1. Born-living, no pause — untouched; still permitted.
2. Abstract/why priority — strengthened, not narrowed. A genuine constraint that
   is also visible in code still extracts: the test is "merely restates", and
   the added rewrite question is what separates the two.
3. Heavy dedup — improved. The absent phase was the reason dedup could not
   happen; Step 3's dedup text is untouched.
4. Optional digest provenance — untouched.
5. One episode review — untouched.
6. Validate, no reindex — untouched.
7. Root-over-decision shape — same Step 2 blurb edited; the root-over-decision
   sentences are intact and the changed clause does not favour `decision`.
8. Born-living + shared deferral test — untouched.

**Ping-pong check:** the 2026-07-23 entry added the batch self-check with a
`Labels` bullet. This edit extends that bullet rather than reversing it — the
vocabulary test is kept verbatim and a shape test added alongside. Same
direction, no oscillation. The evidence that the vocabulary-only test was
insufficient: the rejected labels were drawn from the session's own words and
passed it while being structurally wrong.

**Declined:** no structural rewrite of the orchestrators, and no promotion of
any judgment zone to rules. A mechanical remedy — having `ldoc new` warn when a
`--tags-domain` value matches a `scope` in the doc's own ancestry — would catch
the domain/scope class at the CLI rather than in prose, but that is a CLI change
and is left as a note here rather than performed.
