# live_docs

**A living knowledge graph for a codebase — the decisions, rationale, and intent the code can't tell you, kept true as it changes.**

live_docs holds the durable knowledge about a project — its principles, goals, decisions, constraints, and requirements — as a graph of small, single-responsibility Markdown docs. Every doc is typed, every dependency between docs is explicit, and when one doc changes the system walks the graph and regenerates whatever else is now stale. It is **infrastructure for coding agents**: they read it to understand a codebase, and maintain it so it stays honest.

The current implementation is a stdlib-only CLI (`ldoc`) plus a set of agent skills. But **the CLI is scaffolding — the point is the system**: the model of atomic typed docs, a dependency graph, and cascade-on-change. Reimplement that model elsewhere and the ideas still hold.

---

## The problem: docs rot

Documentation is stale within hours of being written and actively misleading within weeks. So teams stop trusting it, stop reading it, and eventually stop writing it — and the reasoning behind a system (why it's shaped this way, what was decided and rejected, what's aspirational vs. real) lives only in people's heads and old chat logs. Coding agents inherit the same blind spot: they write better code when they understand a repo, but there's no durable, trustworthy place for that understanding to live.

**Drift is the enemy**, and live_docs beats it deliberately: not by regenerating docs from the code (that recovers the *what* and loses the *why*), and not by leaning on human discipline (which fades) — but by keeping the knowledge itself **living**. Atomic, single-responsibility docs; an explicit dependency graph that makes any change's blast radius computable; and a cascade that, when something moves, *surgically regenerates* the affected docs from the graph — the specific stale nodes rewritten to current truth, never flagged-and-forgotten and never left as snapshots to rot.

---

## Five commitments

What makes live_docs itself, in five stances:

- **Docs lead; code aligns.** The docs are the source of truth for *intent*; code reconciles to them, not the reverse. That's what makes a doc/code mismatch a *signal* — drift, or a decision the code hasn't caught up to — rather than an impossibility.
- **The why, not the what.** Capture only what code can't re-derive: the decisions, rationale, constraints, and goals. The *what* is always recoverable from the source; the *why* is not, and it outlives any implementation.
- **Accuracy, not access.** The valuable, hard job is keeping the knowledge accurate as reality changes — a write-time discipline — not fetching it. So live_docs is deliberately unopinionated about your agent harness: RAG, MCP, and prompt-assembly are downstream layers that bolt onto a store that's already true.
- **Living, not snapshotted.** When something changes, cascade *regenerates* the affected docs surgically from the graph — the stale nodes rewritten to current truth. Atomicity is what makes that safe and local.
- **Revisable, not just enforced.** Every decision records its *why* and its dependencies, so it can be safely changed when reality moves — not merely checked against. The rulebook evolves instead of ossifying.

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

**Cascade keeps it living.** When a doc changes, `cascade-check` walks both graphs — upstream dependencies and downstream dependents — and issues a verdict per neighbor: *inconsequential* (stop), *cascade* (regenerate the dependent from the graph), *incompatible* (a conflict a human must resolve), or *needs-clarification*. Most edits are inconsequential; the ones that aren't get their stale docs regenerated to current truth, not just flagged.

**Capture is cheap; ingestion is deliberate.** Raw material (notes, RFCs, chat summaries, research) drops into an inbox instantly, then passes through gates: `inbox → raw → atomic docs`. The final gate — decomposing a blob into single-responsibility docs — is where the value is, and it's never skipped.

**Agents do the work; humans steer.** The heavy lifting (ingesting references, revising docs, gardening the graph, running cascades) is done by [skills](.claude/skills/) — agent procedures that carry the judgment. The `ldoc` CLI underneath is intentionally *dumb*: it writes what it's told and validates references, nothing more. Humans stay in the loop through post-hoc **review** summaries, not by hand-editing files.

**It eats its own cooking.** The knowledge base under [`kb/`](kb/) is live_docs' *own* design documentation — its principles, decisions, and edge model — read and edited with `ldoc` like any other store. Every rough edge in the system is felt first-hand by the people building it. The fastest way to understand live_docs is to install it and run `ldoc map` here.

---

## Quick start

```bash
./install.sh     # puts the `ldoc` CLI on your PATH + installs the skills plugins
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
| `.claude-plugin/`, `.cursor-plugin/` | package the shared skills for Claude Code and Cursor |
| `bin/`, `install.sh`, `mise.toml` | tooling to put `ldoc` on your PATH and install the plugins |
| `docs/` | human-facing guides (setup, and more over time) |
| `reports/` | design analyses and research artifacts (not part of the KB graph) |
