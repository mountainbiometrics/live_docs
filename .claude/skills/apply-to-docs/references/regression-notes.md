# Regression notes — apply-to-docs

Anchors for refinement. Reconstructed 2026-07-23; replace with cited happy-path
outputs when available.

## Known-good properties (must keep permitting)

1. **Identify then synthesize** — full blast-radius survey before any write.
2. **Archive then extract** — raw clipping + normalized reference before concept
   extraction; REQ_ID is the provenance anchor.
3. **Pause gate** only for unresolved conflicts or judged unintended
   side-effects — never solely because the expected impact set is large.
4. **Verbatim request body** into the raw clipping when the input *is* the user's
   request text.
5. **One episode review** owned by this orchestrator.

## Known failure (2026-07-23 / related)

`--source "user-request"` was applied to material the agent authored (user
ratified the idea, not the wording). Hardcoded source string overclaims.
Concept extraction inherited identify-key-concepts without naming
root-over-decision (reconcile had a soft bias that still failed).

## Newly discovered good-output properties (2026-07-23)

6. **Honest `--source`.** Verbatim user text may say `user-request`; agent
   restatements and mixed digests must not.
7. **Pause ≠ rubber-stamp.** A coherent multi-doc update the user asked for
   (e.g. 9 cascade-extends, 0 conflicts) proceeds without a yes/no gate. Pause
   reserves human attention for conflicts and surprises.
