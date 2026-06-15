#!/usr/bin/env bash
# validate.sh — thin wrapper; delegates to scripts/validate.py
# Works regardless of CWD: resolves the repo root relative to this file.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# validate.sh lives in .claude/skills/validate/ — three levels up is the repo root
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"

exec python3 "${REPO_ROOT}/scripts/validate.py" "$@"
