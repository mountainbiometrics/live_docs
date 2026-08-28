# Regression notes — reconcile-changes

Anchors for refinement. Reconstructed 2026-07-23; replace with cited happy-path
outputs when available.

## Known-good properties (must keep permitting)

1. **Born-living, no pause gate.** Already-real changes are recorded, not
   proposed; blast-radius informs synthesis, does not ask permission.
2. **Abstract/why priority over code-mirroring components.** Implementation facts
   the code can re-derive are low-value; principles, goals, use-cases,
   constraints, and decision rationale are the prize.
3. **Heavy dedup.** Prefer revising existing docs over near-duplicate creates.
4. **Optional session digest as provenance anchor.** New docs wire
   `--provenance DIGEST_ID` (or genuine requires/belongs_to) — no floaters.
5. **One episode review**, owned by this orchestrator; nested phases emit none.
6. **Validate after writes**; no reindex in-episode.

## Known failure (2026-07-23, consumer store)

Despite the why-priority knob, a large reconcile still produced a
decision-inventory first pass; user correction was required to elevate root
principles/constraints. Review close did not surface the type-mix / naming /
level smells.

## Newly discovered good-output property (2026-07-23)

7. **Root-over-decision shape.** A successful reconcile concept list / write set
   is dominated by principles/constraints/requirements/goals; decisions exist as
   thin `requires`-linked nodes, not as the primary inventory.

## Newly discovered good-output property (2026-08-04)

8. **Born-living + shared deferral test.** `target` only when
   `_shared/status-living-vs-target.md` passes; session timing alone never
   flips status.

## Known failure (2026-08-10)

An agent ran the orchestrator end to end but performed Steps 3–5 inline instead
of invoking them, writing the batch with raw `ldoc new`. The four shared files
that govern writing — labels, domain/scope, body style, placement — are
referenced only from `synthesize-doc-changes`, so skipping that phase means
never reading any of them. `ldoc validate` passed the whole time.

## Newly discovered good-output properties (2026-08-10)

9. **Write-time discipline is actually reached.** A successful run's docs show
   evidence of `_shared/label-title-summary.md`, `domain-tagging.md`,
   `doc-style.md`, and `belongs-to-placement.md` having been applied — which in
   practice means the batch went through `synthesize-doc-changes` rather than
   straight to `ldoc`.
10. **`domain` only for cross-scope concerns.** A batch whose docs all live in
    one subsystem carries `scope` on its anchor and inherits it; it does not
    coin a domain named after that subsystem.
11. **Labels name, they do not answer.** Each new label reads as a handle for a
    topic a reader would open the doc to learn about, not as the doc's
    conclusion restated. Drawing every word from the session's own vocabulary
    does not make a label correct on this axis.

## Known failure (2026-08-12, consumer store)

A 19-doc reconcile run let born-`living` (status) leak into `level`: ten docs
landed at `preference`/`requirement` because the code implementing them was
built, tested, and committed — though the choices were an implementer's own
convenience, never raised or reviewed by the user. User's verdict on the one
cited by id: "not something that I brought up in any way at all... which is
*incidental* in both literal definition and our guidelines." Two secondary
failures in the same run: a new `level: preference` doc silently contradicted
an existing `level: requirement` doc (nothing in the workflow checked for
this); and two claims the user stated in their own words were recorded weak
and agent-attributed while the convenience built *instead of* one of them was
recorded strong and settled — inverting the record. Root cause: the skill's
own "already-real" rhetoric (justified for `status`) was read as applying to
`level` too, even though the correct level-authority rule already existed
(checklist line, and `synthesize-doc-changes` §level classification).

## Newly discovered good-output properties (2026-08-12)

12. **Differentiated levels, not blanket caution.** In the same failing run,
    five of the nineteen new docs correctly landed at `level: incidental` on
    their own — the level-authority fix must sharpen this discrimination, not
    flatten every new doc to `incidental` regardless of merit. A fix that
    makes `preference`/`requirement` unreachable is as wrong as the failure it
    corrects.
13. **Unprompted correction of a stale claim.** The same pass noticed an
    existing constraint (`Loudly Partial Measurement`) had been recorded
    path-wise so a new mechanism did not actually discharge it, and corrected
    it without being asked. Nobody prompted this; preserve whatever in Step 3
    ("correcting stale existing docs is the highest-value output") lets it
    happen.
14. **Honest self-reporting of uncertainty.** The same pass flagged its own
    open issues — terminology drift it declined to fix, a raw-tier
    linkability gap, a doc left incomplete — rather than presenting the batch
    as fully resolved. Keep whatever in the Step 8 self-check produces this.
