# live_docs

**A living knowledge graph for a codebase — the *why* and *what* that code can't re-derive, kept true as the system changes.**

live_docs holds the durable knowledge about a project — its principles, goals, decisions, constraints, and requirements — as a graph of small, single-responsibility Markdown docs. Every doc is typed, every dependency between docs is explicit, and when one doc changes the system walks the graph to find what else is now stale. It is **infrastructure for coding agents**: a substrate they read to understand a codebase, and maintain so it stays honest.

The current implementation is a stdlib-only CLI (`ldoc`) plus a set of agent skills. But **the CLI is scaffolding — the point is the system**: the model of atomic typed docs, a dependency graph, and cascade-on-change. Reimplement that model on a different substrate and the ideas still hold.

---

## The problem: docs rot

Documentation is stale within hours of being written and actively misleading within weeks. So teams stop trusting it, stop reading it, and eventually stop writing it — and the reasoning behind a system (why it's shaped this way, what was decided and rejected, what's aspirational vs. real) lives only in people's heads and old chat logs. Coding agents inherit the same blind spot: they write better code when they understand a repo, but there's no durable, trustworthy place for that understanding to live.

**Drift is the enemy.** live_docs is a bet that you beat drift not with discipline (which fades) or with regeneration (which throws away intent), but with *structure* — atomicity to keep each fact isolated, an explicit dependency graph so a change's blast radius is computable, and an automated cascade that flags every downstream doc a change touches.

---

## How it works

**Atomic, typed docs.** Each doc is one responsibility — a single principle, decision, constraint, goal, use-case, component, or reference. Filenames are opaque timestamp IDs; the human-readable name lives in a `title` field. Every doc carries typed frontmatter:

```yaml
---
id:      "20260615100017"
title:   "live_docs is the portable system; a consuming store is a specific instance"
label:   "Portable System vs Instance"
summary: "live_docs is a portable, reusable system; a store that consumes it is a specific instance…"
type:    decision        # principle | goal | decision | constraint | requirement | use-case | guide | component | reference
status:  living          # living (current) | target (intended, not yet built) | deprecated | reference
level:   preference      # incidental | trial | preference | requirement
requires: ["[[20260615182358]]"]
---
```

**`status` lets contradictions coexist honestly.** A `living` doc describes current reality; a `target` doc describes where you want to be. The two can disagree without the store being "wrong" — that's how you track a migration or an aspiration without pretending it's already done.

**Two graphs over the same docs.**
- A `belongs_to` **hierarchy** — the navigational tree. Any doc that others belong to is, structurally, a signpost. `ldoc map` prints these entry points, ranked, as the closest thing to a front page.
- A `requires` / `relates` **dependency web** — existential and see-also links that model how the system actually hangs together.

**Cascade fights drift.** When a doc changes, `cascade-check` walks both graphs — upstream dependencies and downstream dependents — and issues a verdict per neighbor: *inconsequential* (stop), *cascade* (propagate the change), *incompatible* (a conflict a human must resolve), or *needs-clarification*. Most edits are inconsequential; the ones that aren't get surfaced instead of silently rotting.

**Capture is cheap; ingestion is deliberate.** Raw material (notes, RFCs, chat summaries, research) drops into an inbox instantly, then passes through gates: `inbox → raw → atomic docs`. The final gate — decomposing a blob into single-responsibility docs — is where the value is, and it's never skipped.

**Agents do the work; humans steer.** The heavy lifting (ingesting references, revising docs, gardening the graph, running cascades) is done by [skills](.claude/skills/) — agent procedures that carry the judgment. The `ldoc` CLI underneath is intentionally *dumb*: it writes what it's told and validates references, nothing more. Humans stay in the loop through post-hoc **review** summaries, not by hand-editing files.

**It eats its own cooking.** The knowledge base under [`kb/`](kb/) is live_docs' *own* design documentation — its principles, decisions, and edge model — read and edited with `ldoc` like any other store. Every rough edge in the system is felt first-hand by the people building it. The fastest way to understand live_docs is to install it and run `ldoc map` here.

---

## Quick start

```bash
./install.sh     # puts the `ldoc` CLI on your PATH + installs the livedocs skills plugin
ldoc map         # orient: the store's entry-point signposts, ranked, with summaries
ldoc help        # the full command surface, grouped, with examples
```

Full setup — installing just one part, attaching another repo to a store, sharing a store across machines — is in **[docs/install.md](docs/install.md)**.

---

## Where to go next

| You want… | Go to |
|-----------|-------|
| To install it, or attach another repo to a store | **[docs/install.md](docs/install.md)** |
| The operating manual for an **AI agent** working in this repo | **[AGENTS.md](AGENTS.md)** |
| A portable, store-agnostic quick-reference (CLI surface, schema, enums, edge model) | the **`reference` skill** — `/livedocs:reference`, or [`.claude/skills/reference/SKILL.md`](.claude/skills/reference/SKILL.md) |
| To browse the design of live_docs itself | run `ldoc map`, then follow edges with `ldoc show <ref>` |
| A read-only visual browser of a store | `ldoc viewer` builds a self-contained HTML view |
| What's on the roadmap | **[WISH.md](WISH.md)** |

---

## Status & scope

live_docs is **early and evolving**, developed in the open. Expect the schema and skills to move. It is deliberately narrow: it models a codebase's durable knowledge and keeps it consistent — it is *not* a retrieval stack, an MCP server, or an agent harness, and it doesn't try to be. Those are meant to layer on top.

The `ldoc` CLI is Python-3 stdlib-only (no dependencies); the skills target [Claude Code](https://claude.com/claude-code) but the store itself is just Markdown files you can read, grep, or open in any text or markdown reader.

---

## Repository layout

| Path | Contents |
|------|----------|
| `kb/` | the knowledge base — live_docs' own docs (`00-inbox/`, `01-raw/`, `02-docs/`, `reviews/`) |
| `scripts/` | the `ldoc` porcelain (`ldoc.py`) and the KB layer (`livedocs/`) |
| `.claude/skills/` | the agent skill definitions |
| `.claude-plugin/` | packages the skills as the installable `livedocs` plugin |
| `bin/`, `install.sh`, `mise.toml` | tooling to put `ldoc` on your PATH and install the plugin |
| `docs/` | human-facing guides (setup, and more over time) |
| `reports/` | design analyses and research artifacts (not part of the KB graph) |
