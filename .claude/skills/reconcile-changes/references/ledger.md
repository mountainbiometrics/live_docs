# Ledger — reconcile-changes

Edit history for skill refinements. Newest first.

## 2026-08-12 — Stop born-`living` from leaking into `level` (Class B, + Class A for level collisions)

**Failure:** A 19-doc reconcile run produced ten docs at `level:
preference`/`requirement` for choices that were an implementer's own
convenience — built, tested, committed, but never raised or reviewed by the
user. User's verdict on the cited doc: "not something that I brought up in
any way at all... which is *incidental* in both literal definition and our
guidelines." Two secondary failures: a new `preference` doc silently
contradicted an existing `requirement` doc (no check anywhere catches this);
and user-stated claims were recorded weak/agent-attributed while a convenience
built in their place was recorded strong/settled, inverting the record.
Separately, the user clarified a `status` rule (`target` is for
initiative-level unbuilt direction or explicit deferral; "not in this
changeset" alone stays `living`) — checked against `_shared/status-living-vs-
target.md` and found already correctly covered there (see Declined).

**Class:**
- **B** — the correct level-authority rule already existed (checklist line
  "Levels reflect claim authority... not 'has provenance edge'"; and
  `synthesize-doc-changes` §level-classification, which defaults new claims to
  `incidental` absent an explicit user utterance). The skill's own framing
  text supported the bad reading: "the resulting docs are born `status:
  living`, not `target`, because they describe reality as it now stands"
  (intro), reinforced by "already happened and is live... recording reality
  that changed" (differs-section), "there is nothing to ask permission for"
  (Step 4), and similar phrasing at the Step 8 self-check header — all
  correct as applied to `status`, but nothing distinguished `level` from that
  frame, so the born-`living` "it's already real" instinct bled across the
  axis.
- **A** — the level-collision check (a new doc's claim contradicting an
  existing higher-`level` doc) had no home anywhere in the pipeline:
  `assess-blast-radius` walks structural impact, not level ordering, and
  nothing else checks it either.

**Diff (this session inherited an uncommitted +42/−2 draft already in the
working tree from an ad hoc pass; evaluated under this skill's discipline
rather than assumed correct or discarded):**
- `reconcile-changes/SKILL.md` intro (after the born-`living` sentence):
  added a disambiguating paragraph — `status` answers "is this settled?",
  `level` answers "who decided this, how deliberately?"; code being
  built/tested/committed is evidence for the former only; names the user's
  stated harm (inertia/friction on unrequested decisions) as the reason it
  matters. Placed at the point of highest leverage — immediately after the
  phrase that most directly permits the bad reading — rather than touching
  every downstream "already real" phrase individually (Step 4's, the
  differs-section's, etc. remain untouched; they are correct as scoped to
  `status`/pause-gate and don't literally reference `level`).
- Step 5 handoff: added an explicit **level-authority test** bullet,
  mirroring the existing born-`living` knob bullet's level of detail —
  convenience-choice → `incidental` regardless of build quality; inherited
  force from a standing requirement takes that requirement's level; a
  user-stated claim keeps its weight even pre-code (status gap, not a level
  gap); names the inversion failure explicitly so it's checked for, not just
  the primary one.
- Step 5: new **level-collision** paragraph — check each new doc's claim
  against the Step 4 impact set for contradiction with a higher-`level`
  existing doc before writing; a lower rung cannot overturn a higher one by
  being newer; surface collisions to the user like `conflict-unresolved`.
- Step 8 self-check: two new bullets, `Levels vs. build status` (smell: level
  correlates with what shipped rather than who asked) and `Level collisions`,
  matching the existing bullet-per-failure-mode pattern.
- Checklist: reworded the levels line to point at the new Step 5 test instead
  of restating the rule inline (no content change, cross-reference only).
- `_shared/status-living-vs-target.md` opening paragraph: one sentence added
  — this file governs `status` alone; `level` is a separate axis and nothing
  here determines it. Read by all three orchestrators that cite this file, so
  the clarification benefits `apply-to-docs` and `ingest-reference` too
  (neither was edited; report-only per scope).

**Regression answers (against `references/regression-notes.md`):**
1. Born-living, no pause gate — untouched; the born-`living` knob bullet and
   "No pre-implementation pause" section are byte-identical pre/post edit.
2. Abstract/why priority — untouched, Step 2 unmodified.
3. Heavy dedup — untouched, Step 3 unmodified.
4. Optional digest provenance — untouched, Step 1 and the digest-anchor
   Step 5 bullet unmodified.
5. One episode review — untouched, Step 0/8 session mechanics unmodified.
6. Validate, no reindex — untouched, Step 7 unmodified.
7. Root-over-decision shape — untouched, Step 2 unmodified.
8. Born-living + shared deferral test — untouched; confirmed by diff, not
   just inference: the born-`living` knob bullet text is unchanged and the
   shared file's `target` test section is unchanged (only preceded by the new
   axis-clarifying sentence).
9. Write-time discipline reached via synthesize-doc-changes — untouched, the
   "Do not write with raw `ldoc new`" paragraph is unmodified.
10. `domain` only for cross-scope — untouched, Step 8's Domain vs scope bullet
    unmodified.
11. Labels name, don't answer — untouched, Step 8's Labels bullet unmodified.
12. Differentiated levels (5/19 correctly `incidental`) — preserved: the added
    text is a discriminating test ("who decided", "convenience → incidental"
    vs. "inherited force from a standing requirement takes that level"), not
    a blanket default toward `incidental`; the blanket-default guidance
    (already scoped correctly with evidence-based promotion) lives in
    `synthesize-doc-changes` and was not touched.
13. Unprompted correction of stale claims — untouched, Step 3's
    highest-value-output framing unmodified.
14. Honest self-reporting — preserved; the two new Step 8 bullets are
    additive within the existing self-check format and don't replace or
    narrow the others.

**Declined:**
- The user's separately-stated `status` clarification ("`target` is for
  initiative-level unbuilt direction or explicit deferral; not-in-changeset
  alone is `living`") needed no new text: `_shared/status-living-vs-
  target.md`'s existing "`target` is not correct merely because... code has
  not caught up to an in-force design" line already states this. Verified by
  re-reading, not assumed.
- Did not touch the other five "already real" passages the brief flagged
  (differs-section, Step 4's no-pause-gate language, Step 8 header) — each
  is correct as scoped to `status`/pause-gate and does not literally mention
  `level`; the one disambiguating paragraph placed at the point of highest
  leverage (immediately after the most direct trigger sentence) was judged
  sufficient, reinforced locally by the Step 5 test and Step 8 checks where
  `level` is actually assigned. Editing all seven would have been the
  scattered, non-minimal version of the same fix.
- No structural rewrite of the orchestrator and no promotion of the
  level-authority *zone* itself to a hard rule — it stays a per-claim test
  ("ask who decided"), not a formula. Only the one concrete case the user
  ratified (implementer convenience choices are never elevated) is stated as
  settled.
- Did not re-run the full 8-step pipeline against live session data to get
  literal before/after outputs (no in-repo working session was available to
  reconcile against); the regression answers above are diff-verified
  (confirming untouched sections are byte-identical) rather than execution-
  verified. Flagging this rather than overstating confidence.

**Ping-pong check:** no prior entry touches `level` semantics in
reconcile-changes; this is new ground, not a reversal.

---

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
