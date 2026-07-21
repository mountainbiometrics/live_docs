#!/usr/bin/env bash
#
# install.sh — set up the live_docs tooling on this machine.
#
# Two independent pieces, both installed by default:
#   1. the `ldoc` CLI  — symlinked onto your PATH (works in any terminal)
#   2. the skills plugin — installed into whichever agent harnesses are present:
#        - Claude Code: marketplace register + user-scope install
#        - Cursor:      symlink into ~/.cursor/plugins/local/ (official local path)
#      Skills live once under .claude/skills/; both manifests point at them.
#
# The store itself is NOT installed or configured here — that is a separate
# concern (like `git` vs `git init`). `ldoc` and the skills locate a store by
# walking up from the current directory for a `.live_docs.toml` marker; to
# attach a repo to a store, add that one-line marker yourself (see `ldoc store`).
#
# Usage:
#   ./install.sh                     # install the CLI + plugins (global)
#   ./install.sh --no-plugin         # CLI only
#   ./install.sh --no-cli            # plugins only
#   ./install.sh --bin-dir ~/bin     # symlink ldoc somewhere other than ~/.local/bin
#   ./install.sh -h | --help
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LDOC_SRC="$REPO_ROOT/scripts/ldoc.py"
MARKETPLACE_NAME="live-docs"
# Claude Code's plugin id (underscore). Cursor forbids underscores in names —
# its manifest uses kebab-case `live-docs` (CURSOR_PLUGIN_NAME).
PLUGIN_NAME="live_docs"
CURSOR_PLUGIN_NAME="live-docs"
CURSOR_LOCAL_DIR="${HOME}/.cursor/plugins/local"
CURSOR_LOCAL_LINK="${CURSOR_LOCAL_DIR}/${CURSOR_PLUGIN_NAME}"

BIN_DIR="${HOME}/.local/bin"
DO_CLI=1
DO_PLUGIN=1

# ── colours (no-op if not a tty) ───────────────────────────────────────────
if [ -t 1 ]; then BOLD=$(tput bold); DIM=$(tput dim); RST=$(tput sgr0); else BOLD=""; DIM=""; RST=""; fi
say()  { printf '%s\n' "$*"; }
step() { printf '\n%s==>%s %s\n' "$BOLD" "$RST" "$*"; }
ok()   { printf '  %s✓%s %s\n' "$BOLD" "$RST" "$*"; }
warn() { printf '  %s!%s %s\n' "$BOLD" "$RST" "$*"; }
die()  { printf '%sinstall.sh: %s%s\n' "$BOLD" "$*" "$RST" >&2; exit 1; }

# ── args ───────────────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
  case "$1" in
    --no-cli)      DO_CLI=0 ;;
    --no-plugin)   DO_PLUGIN=0 ;;
    --bin-dir)     BIN_DIR="${2:?--bin-dir needs a path}"; shift ;;
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

# ── 2. skills plugins (Claude Code + Cursor) ────────────────────────────────
install_claude_plugin() {
  step "Installing the live_docs skills plugin (Claude Code)"
  command -v claude >/dev/null 2>&1 || { warn "the 'claude' CLI is not on PATH — skipping Claude plugin."; return; }

  claude plugin validate "$REPO_ROOT" >/dev/null 2>&1 \
    && ok "manifests valid" \
    || warn "claude plugin validate reported issues (continuing)"

  if claude plugin marketplace list 2>/dev/null | grep -q "$MARKETPLACE_NAME"; then
    ok "marketplace '$MARKETPLACE_NAME' already registered"
  else
    claude plugin marketplace add "$REPO_ROOT" && ok "registered marketplace '$MARKETPLACE_NAME'"
  fi

  # Always reinstall — plugin files are cached by Claude Code, so skipping on
  # "already installed" means updates (new skills, manifest changes) never land.
  if claude plugin list 2>/dev/null | grep -q "$PLUGIN_NAME"; then
    claude plugin uninstall "$PLUGIN_NAME" --scope user 2>/dev/null || true
  fi
  claude plugin install "${PLUGIN_NAME}@${MARKETPLACE_NAME}" --scope user \
    && ok "(re)installed '${PLUGIN_NAME}@${MARKETPLACE_NAME}' (user scope)"
  warn "restart any running Claude Code session to pick up the skills."
}

install_cursor_plugin() {
  step "Installing the live_docs skills plugin (Cursor)"
  # Cursor has no plugin CLI; the documented local path is a symlink under
  # ~/.cursor/plugins/local/<name>. Only install when Cursor has already
  # created ~/.cursor (opened at least once) — don't invent a Cursor home.
  if [ ! -d "${HOME}/.cursor" ]; then
    warn "~/.cursor not found — skipping Cursor plugin (open Cursor once, then re-run)."
    return
  fi
  [ -f "$REPO_ROOT/.cursor-plugin/plugin.json" ] \
    || die "missing $REPO_ROOT/.cursor-plugin/plugin.json"

  mkdir -p "$CURSOR_LOCAL_DIR"

  if [ -L "$CURSOR_LOCAL_LINK" ] && [ "$(readlink "$CURSOR_LOCAL_LINK")" = "$REPO_ROOT" ]; then
    ok "already linked: $CURSOR_LOCAL_LINK -> $REPO_ROOT"
  elif [ -e "$CURSOR_LOCAL_LINK" ] || [ -L "$CURSOR_LOCAL_LINK" ]; then
    warn "$CURSOR_LOCAL_LINK already exists and points elsewhere; leaving it alone."
    warn "remove it and re-run to point it at this checkout."
  else
    ln -s "$REPO_ROOT" "$CURSOR_LOCAL_LINK"
    ok "linked $CURSOR_LOCAL_LINK -> $REPO_ROOT"
  fi
  warn "reload the Cursor window (Developer: Reload Window) to pick up the skills."
}

install_plugin() {
  install_claude_plugin
  install_cursor_plugin
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

# ── run ────────────────────────────────────────────────────────────────────
[ "$DO_CLI" = 1 ]    && install_cli
[ "$DO_CLI" = 1 ]    && bootstrap_user_config
[ "$DO_PLUGIN" = 1 ] && install_plugin

step "Done."
say "  ${DIM}CLI:${RST}    ldoc help"
say "  ${DIM}skills:${RST} /garden, /ingest-reference, … (Claude: /${PLUGIN_NAME}:…; reload Cursor / restart Claude Code)"
say "  ${DIM}store:${RST}  attach a repo to a store with a one-line .live_docs.toml (store = \"<name>\"); register stores with 'ldoc store register'"
