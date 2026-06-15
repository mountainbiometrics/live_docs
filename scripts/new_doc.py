#!/usr/bin/env python3
"""
new_doc.py — Create a new live_docs document.

SHIM: Delegates to `ld new` (scripts/ld.py). All logic lives in livedocs.KB.

Usage (unchanged from original — fully back-compatible):
    python scripts/new_doc.py --type decision --title "Use flat doc store"
    echo "Body text" | python scripts/new_doc.py --type principle --title "Keep it simple" --body -
"""

import sys
from pathlib import Path

# Ensure scripts/ is on sys.path so livedocs is importable from any CWD.
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> None:
    # Re-map sys.argv to ld.py's `new` subcommand, then call its main().
    # We insert 'new' as the first argument so ld.py sees: ld new --type ...
    import ld as ld_module
    sys.argv = [sys.argv[0], "new"] + sys.argv[1:]
    sys.exit(ld_module.main())


if __name__ == "__main__":
    main()
