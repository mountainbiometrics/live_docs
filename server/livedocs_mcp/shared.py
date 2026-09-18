"""
shared.py — make the store's shared code importable.

The endpoint is a second surface over the same library the `ldoc` CLI calls, so
it imports that library rather than shelling out to the CLI. The library is not
an installable package yet — it lives in the repo's `scripts/` directory and is
deliberately stdlib-only — so the path is added here, located relative to this
file.

Importing this module is what does it, so any module that needs `livedocs`
imports this one first and the order cannot come out wrong.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"


def add_shared_code_to_path() -> Path:
    """Put the repo's `scripts/` on sys.path. Returns the directory used."""
    if not (SCRIPTS_DIR / "livedocs" / "model.py").is_file():
        raise SystemExit(
            f"livedocs-mcp: cannot find the live_docs shared code at {SCRIPTS_DIR}.\n"
            f"The endpoint reads it out of the checkout it was installed from, so "
            f"install it from a checkout rather than copying the package:\n"
            f"  uv run --directory <checkout>/server livedocs-mcp\n"
            f"  pip install -e <checkout>/server"
        )
    path = str(SCRIPTS_DIR)
    if path not in sys.path:
        sys.path.insert(0, path)
    return SCRIPTS_DIR


add_shared_code_to_path()
