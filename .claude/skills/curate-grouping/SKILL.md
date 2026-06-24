---
name: curate-grouping
description: >
  DEPRECATED — use /garden or /garden find homes for orphans instead. Thin alias
  forwarding to garden-hierarchy (the structure phase of the garden dispatcher).
  Retained for backward compatibility with existing references.
---

# curate-grouping — Alias for garden-hierarchy

**This skill is deprecated.** Grouping, orphan homes, scope anchors, and branch
re-scoping now live in **`garden-hierarchy`**, invoked by the **`/garden`**
dispatcher (or `/garden find homes for orphans`).

## What to do

1. If the user invoked `/curate-grouping` directly, treat it as a **`/garden`**
   episode: capture START, invoke **`garden-hierarchy`** via the Skill tool, then
   close with one cascade-check + one review (same contract as `/garden`).
2. If nested inside another orchestrator that already owns the episode, invoke
   **`garden-hierarchy`** only — no START, no review.

Read and follow `.claude/skills/garden-hierarchy/SKILL.md`.
