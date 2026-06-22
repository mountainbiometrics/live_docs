#!/usr/bin/env bash
# reindex.sh — thin wrapper; delegates to the installed `ldoc` CLI.
# `ldoc` locates the store by discovery (walks up from CWD for .live_docs.toml),
# so this works from anywhere the current directory belongs to a live_docs store.
set -euo pipefail

exec ldoc reindex "$@"
