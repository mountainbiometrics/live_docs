# Contributing to live_docs

live_docs is early and evolving, and contributions are welcome — ideas and design critique as much as code. The README's framing matters here: **the point is the system** (atomic typed docs, an explicit dependency graph, cascade-on-change); the CLI and skills are its current scaffolding. A sharp issue about the model is worth as much as a patch to the tooling.

Orientation: [README.md](README.md) for the what and why, [docs/install.md](docs/install.md) for setup, and [AGENTS.md](AGENTS.md) for the operating manual — the schema, edge rules, and pipeline that any change has to respect. If you work with a coding agent (we do), point it at AGENTS.md first.

## The three surfaces

| Surface | Where | What it is |
|---------|-------|------------|
| The knowledge base | `kb/` | live_docs' own design docs — the source of truth for *intent* |
| The skills | `.claude/skills/` | prose procedures carrying the judgment (ingest, revise, cascade, garden) |
| The CLI | `scripts/` | the deliberately dumb mutation and validation layer (`ldoc`) |

## The knowledge base: never hand-edit

`kb/` is maintained exclusively through the `ldoc` porcelain and the skills — hand-editing doc files skips validation and corrupts history. If your change alters design intent (a new principle, a reversed decision, a constraint), it should land in the KB, not just in code or README prose: docs lead, code aligns. The review files under `kb/reviews/` are how a human audits what a session changed; a PR that touches `kb/` should include the review record the session produced.

## Skills: read the ledgers first

Skills are refined against observed failures, not speculation. Most carry a `references/ledger.md` (what was changed and why) and `references/regression-notes.md` (properties any future change must keep permitting). Before editing a skill, read both — they exist so that a fix for today's failure doesn't reintroduce one that was already paid for. If your change comes from a failure you observed, append an entry.

## The CLI: raw and direct, on purpose

`scripts/ldoc.py` is Python-3 **stdlib-only, zero dependencies** — and that's a stance, not an oversight. No stack, framework, or packaging has been committed to yet (Python itself is incidental), so the implementation stays raw and direct rather than accreting infrastructure that would have to be unwound later. Concretely:

- **Don't introduce dependencies, frameworks, or packaging scaffolding** as a side effect of another change.
- **Fail loud, never prompt.** Error paths print actionable instructions and exit; nothing may block on interactive input — agents and headless environments are first-class callers.
- If you want to make the case for real infrastructure — a test framework, packaging, a port to another stack — open an issue first. Deliberate investment is a conversation worth having; drive-by scaffolding is not.

## Verifying changes

There is no test suite. That's a current working condition (no framework has been chosen), not a rule — but it shapes what a good contribution looks like:

- Verify with **throwaway checks**: exercise the change against a scratch store, `python3 -c` one-liners, `ldoc` sanity commands.
- Run `ldoc validate` before submitting. It's a weak structural check — references resolve, required fields exist — necessary but nowhere near sufficient. Don't treat passing it as proof.
- **Don't add tests just to have something to run.** Coding agents in particular tend to generate reflexive test files and defensive scaffolding to satisfy their own harness; strip that before submitting. A check is welcome when it holds its own weight, and that's a design conversation (see above), not a default.

## Pull requests

- One concern per PR, and say **why** — this whole project is a bet that the why is the valuable part.
- KB-touching PRs include their review record.
- There's no CI gate; review is human. Make the reviewer's job easy.

## Ideas and roadmap

[WISH.md](WISH.md) is the standing wishlist and a good source of shovel-ready work; issues are the right place for design discussion. If a wish interests you, open an issue to align before building.

By contributing, you agree that your contributions are licensed under the repository's license (see `LICENSE`).
