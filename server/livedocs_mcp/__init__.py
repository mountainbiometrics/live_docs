"""
livedocs_mcp — the live_docs MCP endpoint.

A second surface over the store's shared code, beside the `ldoc` CLI: it answers
Model Context Protocol requests so a reader without a checkout can orient in and
read a store. It exposes the porcelain's read commands alone, under their own
names and semantics, and serves the checkouts on its host rather than a copy.

Packaged apart from the tooling so `ldoc` carries none of its dependencies.
"""

__all__ = ["main"]


def main(argv: "list[str] | None" = None) -> int:
    """Console-script entry point. Imported lazily so `--help` costs nothing."""
    from .cli import main as _main

    return _main(argv)
