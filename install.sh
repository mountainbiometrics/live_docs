#!/usr/bin/env bash
#
# install.sh — set up the live_docs tooling on this machine.
#
# Two independent pieces, both installed by default:
#   1. the `ldoc` CLI  — symlinked onto your PATH (works in any terminal)
#   2. the `livedocs` skills plugin — registered + installed in Claude Code
#      (user scope, so it's available in every project)
#
# The store itself is NOT installed here. `ldoc` and the skills locate it by
# walking up from the current directory for a `.live_docs.toml` marker, so a
# consumer repo just needs that one file (see --init-store below).
#
# Usage:
#   ./install.sh                     # install the CLI + the plugin (global)
#   ./install.sh --no-plugin         # CLI only
#   ./install.sh --no-cli            # plugin only
#   ./install.sh --bin-dir ~/bin     # symlink ldoc somewhere other than ~/.local/bin
#   ./install.sh --init-store DIR    # ALSO write a .live_docs.toml in the CURRENT
#                                    #   directory whose kb/ paths point at DIR
#                                    #   (use this in a consumer repo to point it
#                                    #    at a shared store, e.g. .../mtn/sinai)
#   ./install.sh -h | --help
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LDOC_SRC="$REPO_ROOT/scripts/ldoc.py"
MARKETPLACE_NAME="mtn-livedocs"
PLUGIN_NAME="livedocs"

BIN_DIR="${HOME}/.local/bin"
DO_CLI=1
DO_PLUGIN=1
INIT_STORE=""

# ── colours (no-op if not a tty) ───────────────────────────────────────────
if [ -t 1 ]; then BOLD=$(tput bold); DIM=$(tput dim); RST=$(tput sgr0); else BOLD=""; DIM=""; RST=""; fi
say()  { printf '%s\n' "$*"; }
step() { printf '\n%s==>%s %s\n' "$BOLD" "$RST" "$*"; }
ok()   { printf '  %s✓%s %s\n' "$BOLD" "$RST" "$*"; }
warn() { printf '  %s!%s %s\n' "$BOLD" "$RST" "$*" >&2; }
die()  { printf '%sinstall.sh: %s%s\n' "$BOLD" "$*" "$RST" >&2; exit 1; }

# ── args ───────────────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
  case "$1" in
    --no-cli)      DO_CLI=0 ;;
    --no-plugin)   DO_PLUGIN=0 ;;
    --bin-dir)     BIN_DIR="${2:?--bin-dir needs a path}"; shift ;;
    --init-store)  INIT_STORE="${2:?--init-store needs a directory}"; shift ;;
    -h|--help)     awk 'NR>1{ if ($0 !~ /^#/) exit; sub(/^# ?/,""); print }' "$0"; exit 0 ;;
    *)             die "unknown option: $1 (try --help)" ;;
  esac
  shift
done

# ── 1. ldoc CLI ────────────────────────────────────────────────────────────
install_cli() {
  step "Installing the ldoc CLI"
  [ -f "$LDOC_SRC" ] || die "cannot find $LDOC_SRC — run this script from inside the live_docs repo"
  mkdir -p "$BIN_DIR"
  local dest="$BIN_DIR/ldoc"

  if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$LDOC_SRC" ]; then
    ok "already linked: $dest -> $LDOC_SRC"
  elif [ -e "$dest" ] || [ -L "$dest" ]; then
    warn "$dest already exists and points elsewhere; leaving it alone."
    warn "remove it and re-run, or use --bin-dir to pick another location."
  else
    ln -s "$LDOC_SRC" "$dest"
    ok "linked $dest -> $LDOC_SRC"
  fi

  case ":$PATH:" in
    *":$BIN_DIR:"*) ok "$BIN_DIR is on your PATH" ;;
    *) warn "$BIN_DIR is NOT on your PATH — add it, e.g.:"
       warn "    echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.zshrc" ;;
  esac
}

# ── 2. livedocs skills plugin ──────────────────────────────────────────────
install_plugin() {
  step "Installing the livedocs skills plugin (Claude Code)"
  command -v claude >/dev/null 2>&1 || { warn "the 'claude' CLI is not on PATH — skipping plugin install."; return; }

  claude plugin validate "$REPO_ROOT" >/dev/null 2>&1 \
    && ok "manifests valid" \
    || warn "claude plugin validate reported issues (continuing)"

  if claude plugin marketplace list 2>/dev/null | grep -q "$MARKETPLACE_NAME"; then
    ok "marketplace '$MARKETPLACE_NAME' already registered"
  else
    claude plugin marketplace add "$REPO_ROOT" && ok "registered marketplace '$MARKETPLACE_NAME'"
  fi

  if claude plugin list 2>/dev/null | grep -q "$PLUGIN_NAME"; then
    ok "plugin '$PLUGIN_NAME' already installed"
  else
    claude plugin install "${PLUGIN_NAME}@${MARKETPLACE_NAME}" --scope user \
      && ok "installed '${PLUGIN_NAME}@${MARKETPLACE_NAME}' (user scope)"
  fi
  warn "restart any running Claude Code session to pick up the skills."
}

# ── 3. user config bootstrap ───────────────────────────────────────────────
bootstrap_user_config() {
  step "User config (~/.config/live_docs/config.toml)"
  local ldoc="$BIN_DIR/ldoc"
  if [ ! -x "$ldoc" ]; then
    ldoc="python3 $LDOC_SRC"
  fi

  if "$ldoc" config user.name >/dev/null 2>&1; then
    ok "user identity already set ($("$ldoc" config signer 2>/dev/null))"
    return
  fi

  if "$ldoc" config --bootstrap-from-git; then
    ok "bootstrapped review sign-off from git config --global"
  else
    warn "could not bootstrap user config from git"
  fi
}

# ── 4. (optional) consumer .live_docs.toml ────────────────────────────────
init_store() {
  step "Writing .live_docs.toml in $(pwd)"
  local store
  store="$(cd "$INIT_STORE" 2>/dev/null && pwd)" || die "--init-store: no such directory: $INIT_STORE"
  local toml="./.live_docs.toml"
  if [ -e "$toml" ]; then
    warn "$toml already exists — not overwriting. Remove it and re-run to regenerate."
    return
  fi
  cat > "$toml" <<EOF
# live_docs store config — points this repo at a shared store.
# Discovered by walking up from the working directory; paths resolve relative
# to THIS file's directory unless absolute (as below).
inbox   = "$store/kb/00-inbox"
raw     = "$store/kb/01-raw"
docs    = "$store/kb/02-docs"
reviews = "$store/kb/reviews"
EOF
  ok "wrote $toml -> store at $store"
  ok "verify with:  ldoc count"
}

# ── run ────────────────────────────────────────────────────────────────────
[ "$DO_CLI" = 1 ]    && install_cli
[ "$DO_CLI" = 1 ]    && bootstrap_user_config
[ "$DO_PLUGIN" = 1 ] && install_plugin
[ -n "$INIT_STORE" ] && init_store

step "Done."
say "  ${DIM}CLI:${RST}    ldoc help"
say "  ${DIM}skills:${RST} /${PLUGIN_NAME}:garden, /${PLUGIN_NAME}:ingest-reference, … (restart Claude Code first)"
say "  ${DIM}store:${RST}  drop a .live_docs.toml in a repo (or run --init-store) to point it at one"
