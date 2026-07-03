"""
store_registry.py — the `ldoc store` command: register / list / forget named stores.

A store declares its own `name` in its `.live_docs.toml`; consumers reference it
with `store = "<name>"`. The name->location binding is per-user and per-machine,
kept in ~/.config/live_docs/config.toml as `[store.<name>]` tables. This module
is the explicit CLI over that registry; `ldoc` also self-registers a store the
first time it runs inside it (see model._self_register_store).

Store-free: needs no resolvable store to run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ._paths import CONFIG_FILENAME, HOME_CONFIG
from .toml_flat import (
    NAME_KEY,
    ConfigChainError,
    _delegate_target,
    _load_parsed,
    read_store_registry,
    remove_store_registry_entry,
    set_store_registry_entry,
)


def _store_name_at(path: Path) -> tuple[str | None, str | None]:
    """Read the declared name of the store at ``path`` (a dir or its config file).

    Returns (name, error): exactly one is set. Fails loud when the path has no
    config, is a consumer pointer rather than a store, or declares no name.
    """
    cfg = path / CONFIG_FILENAME if path.is_dir() else path
    if not cfg.is_file():
        return None, f"no {CONFIG_FILENAME} found at {path}"
    data = _load_parsed(cfg)
    if _delegate_target(data):
        return None, (
            f"{path} is a consumer marker (it points at another store via "
            f"'store'), not a store itself — register the store it points to."
        )
    name = data.get(NAME_KEY)
    if not isinstance(name, str) or not name.strip():
        return None, (
            f"the store at {path} has no 'name' — add 'name = \"<name>\"' to its "
            f"{CONFIG_FILENAME} so it can be registered."
        )
    return name.strip(), None


def _discover_store_dir() -> tuple[Path | None, str | None]:
    """Find the store we're standing in (walk up for a marker). Returns (dir, error)."""
    from .model import _find_config

    cfg, _searched = _find_config()
    if cfg is None or cfg == HOME_CONFIG:
        return None, (
            "no live_docs store found here. Run this inside a store's checkout, "
            "or pass the path: ldoc store register <path-to-store>"
        )
    return cfg.parent, None


def cmd_register(args: argparse.Namespace) -> int:
    if args.path:
        store_dir = Path(args.path).expanduser().resolve()
    else:
        store_dir, err = _discover_store_dir()
        if err:
            print(f"ERROR: {err}", file=sys.stderr)
            return 1

    declared, err = _store_name_at(store_dir)
    if err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1
    name = args.alias or declared

    status, old = set_store_registry_entry(HOME_CONFIG, name, store_dir, force=args.force)
    if status == "conflict":
        print(
            f"ERROR: store '{name}' is already registered to {old}, not {store_dir}.\n"
            f"       Re-point it with --force, or register under a different local "
            f"name with --alias <name>.",
            file=sys.stderr,
        )
        return 1

    label = f"'{name}'" if not args.alias else f"'{name}' (alias for declared '{declared}')"
    if status == "unchanged":
        print(f"store {label} already registered -> {store_dir}")
    else:
        verb = "updated" if status == "updated" else "registered"
        print(f"{verb} store {label} -> {store_dir}  (in {HOME_CONFIG})")
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    reg = read_store_registry(HOME_CONFIG)
    if not reg:
        print(f"(no stores registered — file: {HOME_CONFIG})")
        return 0
    width = max(len(n) for n in reg)
    for name in sorted(reg):
        root = reg[name]
        missing = "" if (Path(root).expanduser() / CONFIG_FILENAME).is_file() else "  (missing)"
        print(f"{name.ljust(width)}  {root}{missing}")
    return 0


def cmd_forget(args: argparse.Namespace) -> int:
    if remove_store_registry_entry(HOME_CONFIG, args.name):
        print(f"forgot store '{args.name}'  (in {HOME_CONFIG})")
        return 0
    print(f"ERROR: store '{args.name}' is not registered.", file=sys.stderr)
    return 1


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ldoc store",
        description=(
            "Register / list / forget named stores in "
            "~/.config/live_docs/config.toml. A consumer marker references a "
            "store by name (store = \"<name>\"); registration maps that name to "
            "its local checkout on this machine."
        ),
    )
    sub = p.add_subparsers(dest="store_verb", metavar="verb")
    sub.required = True

    pr = sub.add_parser(
        "register",
        help="Register a store (reads its declared name). Defaults to the store you're in.",
    )
    pr.add_argument("path", nargs="?", help="Path to the store (default: the store you're standing in).")
    pr.add_argument("--alias", metavar="NAME", help="Register under a user-chosen local name instead of the declared one.")
    pr.add_argument("--force", action="store_true", help="Re-point an existing binding to this location.")
    pr.set_defaults(func=cmd_register)

    pl = sub.add_parser("list", help="List registered stores and their local paths.")
    pl.set_defaults(func=cmd_list)

    pf = sub.add_parser("forget", help="Remove a store from the registry.")
    pf.add_argument("name", help="Registered store name to forget.")
    pf.set_defaults(func=cmd_forget)

    return p


def run_store_cli(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ConfigChainError as e:
        # e.g. a malformed home config — fail loud, not a raw traceback.
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
