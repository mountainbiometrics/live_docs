"""
store_registry.py — the `ldoc store` command: register / list / forget named stores.

A store declares its own `name` in its `.live_docs.toml`; consumers reference it
with `store = "<name>"`. The name->location binding is per-user and per-machine,
kept in ~/.config/live_docs/config.toml as `[store.<name>]` tables. This module
is the explicit CLI over that registry; `ldoc` also self-registers a store the
first time it runs inside it (see store._self_register_store).

Store-free: needs no resolvable store to run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ._paths import CONFIG_FILENAME, HOME_CONFIG
from .toml_flat import NAME_KEY, ConfigChainError, _load_parsed
from .store import (
    _delegate_target,
    normalize_store_url,
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
    from .store import _find_config

    cfg, _searched = _find_config(Path.cwd())
    if cfg is None or cfg == HOME_CONFIG:
        return None, (
            "no live_docs store found here. Run this inside a store's checkout, "
            "or pass the path: ldoc store register <path-to-store>"
        )
    return cfg.parent, None


def _report_binding(status: str, label: str, location: str, existing: "str | None",
                    rebind_hint: str) -> int:
    """Say what a registration did, or why it refused. Returns the exit code.

    Both kinds of location report the same three outcomes; only the words for the
    store and for re-registering under another name differ.
    """
    if status == "conflict":
        print(
            f"ERROR: store {label} is already registered to {existing}, not "
            f"{location}.\n"
            f"       Re-point it with --force, or register under a different local "
            f"name{rebind_hint}.",
            file=sys.stderr,
        )
        return 1
    if status == "unchanged":
        print(f"store {label} already registered -> {location}")
    else:
        verb = "updated" if status == "updated" else "registered"
        print(f"{verb} store {label} -> {location}  (in {HOME_CONFIG})")
    return 0


def _register_url(args: argparse.Namespace) -> int:
    """Bind a name to a host that serves the store, rather than to a checkout.

    The name is given rather than read off a config, because there is nothing
    local to read it from; --remote-name covers a host that serves the store
    under a different name than the one this machine uses for it.
    """
    name = (args.path or "").strip()
    if not name:
        print("ERROR: give the local name for the store: "
              "ldoc store register <name> --url <endpoint-url>", file=sys.stderr)
        return 1
    if args.alias:
        print("ERROR: --alias names a store whose config declares its own name; "
              "with --url the name you pass IS the local name.", file=sys.stderr)
        return 1

    url = normalize_store_url(args.url)
    remote_name = (args.remote_name or "").strip() or name
    status, old = set_store_registry_entry(
        HOME_CONFIG, name, url=url, remote_name=remote_name, force=args.force,
    )
    served = "" if remote_name == name else f" (served there as '{remote_name}')"
    return _report_binding(status, f"'{name}'", f"{url}{served}", old, "")


def cmd_register(args: argparse.Namespace) -> int:
    if args.url:
        return _register_url(args)
    if args.remote_name:
        print("ERROR: --remote-name only applies to a url location; pass --url too.",
              file=sys.stderr)
        return 1
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

    status, old = set_store_registry_entry(
        HOME_CONFIG, name, root=store_dir, force=args.force,
    )
    label = f"'{name}'" if not args.alias else f"'{name}' (alias for declared '{declared}')"
    return _report_binding(status, label, str(store_dir), old, " with --alias <name>")


def cmd_list(_args: argparse.Namespace) -> int:
    registry = read_store_registry(HOME_CONFIG)
    if not registry:
        print(f"(no stores registered — file: {HOME_CONFIG})")
        return 0
    width = max(len(n) for n in registry)
    for name in sorted(registry):
        entry = registry[name]
        if entry.is_remote:
            served = "" if entry.served_as == name else f"  (as {entry.served_as})"
            print(f"{name.ljust(width)}  {entry.url}{served}")
        else:
            # Only a local checkout can be asked whether a store is really there
            # without making a request of another machine.
            missing = "" if (Path(entry.root).expanduser() / CONFIG_FILENAME).is_file() \
                else "  (missing)"
            print(f"{name.ljust(width)}  {entry.root}{missing}")
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
            "store by name (store = \"<name>\"); registration maps that name to a "
            "location on this machine — a local checkout, or the url of a host "
            "that serves it (read-only from here)."
        ),
    )
    sub = p.add_subparsers(dest="store_verb", metavar="verb")
    sub.required = True

    pr = sub.add_parser(
        "register",
        help="Register a store (reads its declared name). Defaults to the store you're in.",
    )
    pr.add_argument("path", nargs="?",
                    help="Path to the store (default: the store you're standing in), "
                         "or the local NAME when --url is given.")
    pr.add_argument("--alias", metavar="NAME", help="Register under a user-chosen local name instead of the declared one.")
    pr.add_argument("--url", metavar="URL",
                    help="Bind the name to a host serving the store (its MCP endpoint "
                         "url) instead of a local checkout. Read-only from here.")
    pr.add_argument("--remote-name", dest="remote_name", metavar="NAME",
                    help="The name the host serves the store under, when it differs "
                         "from the local name. Only with --url.")
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
