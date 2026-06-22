"""
user_config.py — Per-user ldoc preferences in ~/.config/live_docs/config.toml.

Git-compatible layout:

    [user]
    name = "Samuel Wecker"
    email = "samuel@themtn.ai"

Default review sign-off uses git's author format: ``Name <email>``.

The same file may also hold store-path fallbacks when no `.live_docs.toml` is
found; user and store keys coexist without interfering.

Stdlib only. No store discovery — safe to import before a store is located.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

from .toml_flat import read_config_file, write_config_file

HOME_CONFIG: Path = Path.home() / ".config" / "live_docs" / "config.toml"

USER_KEYS = ("user.name", "user.email")


def load_home_config() -> dict[str, Any]:
    """Return the full parsed home config (user table + optional store paths)."""
    return read_config_file(HOME_CONFIG)


def _get_dotted(data: dict[str, Any], key: str) -> str | None:
    parts = key.split(".")
    cur: Any = data
    for part in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    if cur is None:
        return None
    value = str(cur).strip()
    return value or None


def _set_dotted(data: dict[str, Any], key: str, value: str) -> None:
    parts = key.split(".")
    cur = data
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value.strip()


def _unset_dotted(data: dict[str, Any], key: str) -> None:
    parts = key.split(".")
    cur: Any = data
    for part in parts[:-1]:
        if not isinstance(cur, dict):
            return
        cur = cur.get(part)
    if isinstance(cur, dict):
        cur.pop(parts[-1], None)
    # Drop an empty [user] table.
    user = data.get("user")
    if isinstance(user, dict) and not user:
        data.pop("user", None)


def format_signer(name: str | None, email: str | None) -> str | None:
    """Git author-line format: ``Name <email>``, or whichever part is set."""
    name = (name or "").strip()
    email = (email or "").strip()
    if name and email:
        return f"{name} <{email}>"
    return name or email or None


def _signer_from_data(data: dict[str, Any]) -> str | None:
    """Derive the signer string from an already-loaded config dict."""
    name = _get_dotted(data, "user.name")
    email = _get_dotted(data, "user.email")
    # One-release fallback for the flat ``username`` key.
    if not name:
        legacy = data.get("username")
        if isinstance(legacy, str) and legacy.strip():
            name = legacy.strip()
    return format_signer(name, email)


def get_signer() -> str | None:
    """Configured default sign-off string, or None if unset."""
    return _signer_from_data(load_home_config())


def set_user_key(key: str, value: str) -> None:
    if key not in USER_KEYS:
        known = ", ".join(USER_KEYS)
        raise ValueError(f"unknown user config key {key!r} (known: {known})")

    data = load_home_config()
    _set_dotted(data, key, value)
    write_config_file(HOME_CONFIG, data)


def unset_user_key(key: str) -> None:
    if key not in USER_KEYS:
        known = ", ".join(USER_KEYS)
        raise ValueError(f"unknown user config key {key!r} (known: {known})")

    data = load_home_config()
    _unset_dotted(data, key)
    write_config_file(HOME_CONFIG, data)


def bootstrap_from_git() -> int:
    """Copy ``user.name`` / ``user.email`` from ``git config --global`` if unset."""
    data = load_home_config()
    if _get_dotted(data, "user.name"):
        print(f"user.name already set ({_signer_from_data(data)})")
        return 0

    try:
        proc = subprocess.run(
            ["git", "config", "--global", "--get", "user.name"],
            capture_output=True,
            text=True,
        )
        git_name = proc.stdout.strip() if proc.returncode == 0 else ""
        proc = subprocess.run(
            ["git", "config", "--global", "--get", "user.email"],
            capture_output=True,
            text=True,
        )
        git_email = proc.stdout.strip() if proc.returncode == 0 else ""
    except OSError:
        print("git not available — skipped bootstrap", file=sys.stderr)
        return 0

    if not git_name and not git_email:
        print("no git user.name/user.email to copy")
        return 0

    if git_name:
        set_user_key("user.name", git_name)
    if git_email:
        set_user_key("user.email", git_email)

    print(f"Bootstrapped from git: {get_signer()}")
    return 0


def _build_config_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ldoc config",
        description=(
            "Read or write user preferences in ~/.config/live_docs/config.toml "
            "(git-style user.name / user.email)."
        ),
    )
    p.add_argument(
        "--list", "-l",
        action="store_true",
        help="List user preference keys and values.",
    )
    p.add_argument(
        "--unset",
        metavar="KEY",
        help="Remove a user preference key (e.g. user.email).",
    )
    p.add_argument(
        "--bootstrap-from-git",
        action="store_true",
        help="Copy user.name and user.email from git config --global if unset.",
    )
    p.add_argument("key", nargs="?", help="Preference key (e.g. user.name).")
    p.add_argument("value", nargs="?", help="Value to set (omit to read the current value).")
    return p


def run_config_cli(argv: list[str] | None = None) -> int:
    args = _build_config_parser().parse_args(argv)

    if args.bootstrap_from_git:
        return bootstrap_from_git()

    if args.unset:
        try:
            unset_user_key(args.unset)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
        print(f"Unset {args.unset!r} in {HOME_CONFIG}")
        return 0

    if args.list:
        data = load_home_config()
        printed = False
        for key in USER_KEYS:
            value = _get_dotted(data, key)
            if value:
                print(f"{key}={value}")
                printed = True
        signer = _signer_from_data(data)
        if signer:
            print(f"signer={signer}")
            printed = True
        if not printed:
            print(f"(no user preferences set — file: {HOME_CONFIG})")
        return 0

    if not args.key:
        _build_config_parser().print_help()
        return 0

    if args.value is None:
        if args.key == "signer":
            signer = get_signer()
            if not signer:
                print(f"ERROR: signer is not configured (file: {HOME_CONFIG})", file=sys.stderr)
                return 1
            print(signer)
            return 0
        if args.key not in USER_KEYS:
            known = ", ".join((*USER_KEYS, "signer"))
            print(f"ERROR: unknown key {args.key!r} (known: {known})", file=sys.stderr)
            return 1
        value = _get_dotted(load_home_config(), args.key)
        if not value:
            print(f"ERROR: {args.key!r} is not set (file: {HOME_CONFIG})", file=sys.stderr)
            return 1
        print(value)
        return 0

    if args.key not in USER_KEYS:
        known = ", ".join(USER_KEYS)
        print(f"ERROR: unknown key {args.key!r} (known: {known})", file=sys.stderr)
        return 1

    try:
        set_user_key(args.key, args.value)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"Set {args.key} = {args.value!r} in {HOME_CONFIG}")
    return 0
