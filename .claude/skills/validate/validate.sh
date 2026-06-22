#!/usr/bin/env bash
# validate.sh — thin wrapper; delegates to the installed `ldoc` CLI.
# `ldoc` locates the store by discovery (walks up from CWD for .living_doc.toml),
# so this works from anywhere the current directory belongs to a live_docs store.
set -euo pipefail

exec ldoc validate "$@"
