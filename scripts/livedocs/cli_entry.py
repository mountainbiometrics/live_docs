"""
cli_entry.py — how a live_docs command-line entry point ends.

Store resolution raises rather than exiting, so every script that is also a
command has to decide what "no store here" means to its user. They all decide
the same thing, so they say it once here.

Stdlib only. No external dependencies.
"""

from __future__ import annotations

import sys

from .store import LivedocsConfigError


def config_error_message(e: LivedocsConfigError) -> str:
    """Render a store-resolution failure for a command-line user."""
    return f"ldoc: {e}\n"


def run_cli(main) -> None:
    """Run a command-line entry point, ending the process the way ldoc always has."""
    try:
        sys.exit(main())
    except LivedocsConfigError as e:
        sys.stderr.write(config_error_message(e))
        sys.exit(2)
