# Installing and attaching live_docs

live_docs has three independent parts. The **CLI** and the **skills** are installed once, per machine / per user. A **store** is attached per repo with a one-line marker file — attaching a repo to a store is a separate concern from installing the tool (think `git` vs. `git init`).

| Part | What it is | Scope |
|------|-----------|-------|
| `ldoc` CLI | `scripts/ldoc.py`, symlinked onto your PATH | one machine-wide install; works in any terminal |
| skills plugin | shared skills under `.claude/skills/`, packaged for Claude Code (`.claude-plugin/`) and Cursor (`.cursor-plugin/`) | one user-scope install per harness; available in every project |
| the **store** | the `kb/` graph, located by a `.live_docs.toml` marker | per consumer repo — just the marker file |

---

## Quick start

From inside this repo:

```bash
./install.sh                 # ldoc CLI on PATH + skills plugins (user scope)
```

That symlinks `ldoc` into `~/.local/bin`, installs the Claude Code plugin when `claude` is on `PATH`, and symlinks this repo into `~/.cursor/plugins/local/live-docs` when `~/.cursor` exists. It's idempotent — safe to re-run. Restart Claude Code / reload the Cursor window afterward to pick up the skills.

Useful flags: `--no-plugin` / `--no-cli` to install just one part, `--bin-dir DIR` to link `ldoc` elsewhere. Run `./install.sh --help` for the full list. (Installing the tool never touches a store.)

After installing, invoke skills as `/garden`, `/ingest-reference`, `/validate`, and so on (Claude Code also accepts the `/livedocs:…` namespace).

---

## Manual / partial setup

If you'd rather not run the script, the two install steps are:

```bash
# CLI — any PATH dir works; ldoc.py is stdlib-only
ln -s /path/to/live_docs/scripts/ldoc.py ~/.local/bin/ldoc

# Claude Code skills plugin
claude plugin marketplace add /path/to/live_docs
claude plugin install live_docs@live-docs       # --scope user is the default

# Cursor skills plugin (no CLI — official local path is a symlink)
mkdir -p ~/.cursor/plugins/local
ln -s /path/to/live_docs ~/.cursor/plugins/local/live-docs
```

Working *inside this repo*, `ldoc` is also provided via [`mise`](https://mise.jdx.dev/) (`mise trust` once per machine) without any global install.

---

## Attaching a repo to a store

The CLI and skills are store-agnostic: they operate on whichever store the current directory's `.live_docs.toml` points at. Attaching a repo to a store is just a one-line marker at the repo's root:

```bash
# 1. register the store once — self-registers on any ldoc command run inside it,
#    or do it explicitly (reads the name the store declares in its config):
cd /path/to/store && ldoc store register

# 2. point a consumer repo at it by name (create the one-line marker):
cd /path/to/consumer-repo
[ -e .live_docs.toml ] || echo 'store = "<name>"' > .live_docs.toml   # won't clobber an existing one
ldoc count                                  # confirm it resolves
```

The marker can also point by path — `store = "/path/to/store"` — when you don't need the cross-machine portability of a name. See [Named stores](#named-stores) below.

`ldoc` discovers a store by walking up from the working directory looking for a `.live_docs.toml`, falling back to `~/.config/live_docs/config.toml`. Paths inside the config resolve relative to the file that defined them (absolute and `~` honored), so the docs need not live in the same repo as the code that reads them — a single store can serve several related repos.

---

## Named stores

For sharing one store across machines, commit a **name** rather than a path. A store declares its own `name`:

```toml
# the shared store's .live_docs.toml
name = "acme-docs"
base = "kb"
```

and a consumer references it by that name:

```toml
# a code repo's .live_docs.toml
store = "acme-docs"
```

The name is committable (the same everywhere); each machine maps it to a local checkout in `~/.config/live_docs/config.toml` as `[store.<name>] root = "…"`. `ldoc` **self-registers** a named store the first time you run it inside that store — idempotent, and it never silently repoints a name (a conflicting registration fails loud). An unregistered or moved name also fails loud, with the command to fix it. Manage the registry directly with:

```bash
ldoc store register [path]        # register the store you're in (or the one at <path>)
ldoc store register --alias NAME  # register under a local name (collision escape hatch / preference)
ldoc store register --force       # re-point an existing name to this location
ldoc store list
ldoc store forget <name>
```

---

## `.live_docs.toml` reference

The config is discovered by walking up from the working directory. Keys:

- **`base`** — set the KB parent directory once; omitted box keys default to the numbered layout under it (`00-inbox`, `01-raw`, `02-docs`, `reviews`). Explicit per-box keys still override.
- **`store`** — point this repo at an external store, by **registered name** or by path. A consumer repo is **not** itself a store — it carries only a marker that points elsewhere, so `store` is a *pointer, not inheritance*. All store path keys on a delegating marker are ignored; layout comes wholly from the target, so changing the shared store config once updates every consumer.
- **`[viewer]`** — optional HTML viewer presentation (`title`, `subtitle`, `favicon`, domain colors, type icons); baked into `build/viewer.html` at `ldoc viewer` build time. See below.

`STORE_ROOT` is where the KB lives (the shared store root when delegating); `CONSUMER_ROOT` is where the discovered local marker lives (the code repo). They coincide when a repo owns its store. Generated artifacts such as `build/viewer.html` land under `STORE_ROOT`, never the consumer. Per-key `LIVEDOCS_*_DIR` environment variables override the file for a single invocation.

### `[viewer]` — HTML viewer presentation

Optional table read from the store's `.live_docs.toml` at `ldoc viewer` build time and baked into `build/viewer.html`. Paths resolve relative to `STORE_ROOT` (absolute and `~` also work).

| Key | Type | Default | Effect |
|-----|------|---------|--------|
| `title` | string | `live_docs` | Browser tab title (`<title>`) and navbar heading |
| `subtitle` | string | `viewer · read-only` | Small subtitle beside the heading |
| `favicon` | path | — | Image file embedded as a data-URI favicon |

**Domain colors** — `[viewer.domain_colors]` (alias: `[viewer.domains]`). Keys are domain tag names. Values may be:

- A hex color string (`"#5b6e8c"`) — used for node rings and pill foreground; background/border are derived.
- A table `{ bg = "...", fg = "...", border = "..." }` — used verbatim for domain pills and graph node strokes.

**Type icons** — `[viewer.type_icons]` (alias: `[viewer.types]`). Keys are doc `type` enum values. Each entry may set:

- `color` — stroke/fill hue for the inline Lucide glyph and graph node fill
- `label` — legend/tooltip name override
- `svg` — inner SVG path markup (Lucide 24×24 viewBox) replacing the built-in glyph for that type

Unknown types keep the viewer's built-in fallback icon. Omitted types keep their built-in glyphs and colors.

Example:

```toml
[viewer]
title = "ACME design docs"
subtitle = "internal knowledge base"
favicon = "assets/favicon.png"

[viewer.domain_colors]
platform = "#5b6e8c"

[viewer.type_icons.decision]
color = "#3f7a55"
```
