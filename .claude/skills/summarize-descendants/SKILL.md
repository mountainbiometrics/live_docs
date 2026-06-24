---
name: summarize-descendants
description: >
  Alias for garden-summarize — write a descendant-bearing doc's orientation
  guide and tight summary. Prefer /garden for maintenance episodes; this name is
  kept so cascade-check and legacy references keep resolving. Can be invoked
  standalone (owns its own episode) or nested (caller owns the episode).
---

# summarize-descendants — Alias for garden-summarize

The implementation lives in **`garden-summarize`**. Read and follow
`.claude/skills/garden-summarize/SKILL.md`.

## Episode ownership

- **Standalone** (user invoked this skill directly): capture START, run the
  procedure, validate, emit one `ldoc review new`.
- **Nested** (called from `garden`, `garden-hierarchy`, or `cascade-check`):
  follow the nested contract in `garden-summarize` — no START, no review.

When standalone, use history entry prefix `summarize-descendants:` for continuity
with prior review snapshots.
