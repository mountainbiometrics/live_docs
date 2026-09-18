"""
toml_flat.py — TOML read/write for live_docs config files.

Text in, nested dict out, and back again: a `[user]` table (name, email), flat
top-level store path keys, and `[store.<name>]` tables. What any of those keys
mean, and where they lead, is store.py's.

Stdlib only; uses tomllib/tomli when available, else a small fallback parser.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

STORE_KEYS = ("inbox", "raw", "docs", "reviews", "sessions", "lexicon", "index")
BOX_KEYS = ("inbox", "raw", "docs", "reviews", "sessions", "lexicon")
STORE_CONFIG_KEYS = ("base", *STORE_KEYS)

# A consumer marker points at an external store with ``store`` — either a path
# or a registered store name. Its presence means "this file is a pointer, not a
# store": the marker's own path keys are ignored and layout comes wholly from
# the target store's config.
STORE_KEY = "store"

# A store may declare its own portable ``name``. Consumers reference it by that
# name, and ``ldoc`` self-registers name -> local root in the per-user config
# when run inside the store.
NAME_KEY = "name"

# Keys that may live on a consumer marker alongside ``store``. Store path keys
# on a delegating marker are ignored — the external store owns layout. Reserved
# for future multi-repo hints (e.g. a default scope).
CONSUMER_KEYS: tuple[str, ...] = ()

# Default subdirectories under `base` (numbered KB box layout).
BASE_DEFAULT_SUBDIRS: dict[str, str] = {
    "inbox": "00-inbox",
    "raw": "01-raw",
    "docs": "02-docs",
    "reviews": "reviews",
    "sessions": "sessions",
    "lexicon": "lexicon",
}


class ConfigChainError(Exception):
    """Invalid store-delegation chain or unreadable config file."""


# Resolve the TOML backend once at import time; avoid repeated failed imports.
try:
    import tomllib as _toml_backend  # py3.11+
except ModuleNotFoundError:
    try:
        import tomli as _toml_backend  # type: ignore[no-redef]  # optional backport
    except ModuleNotFoundError:
        _toml_backend = None  # type: ignore[assignment]


def _parse_value(raw: str) -> str:
    val = raw.strip()
    if val and val[0] in "\"'":
        quote = val[0]
        end = val.find(quote, 1)
        return val[1:end] if end != -1 else val[1:]
    return val.split("#", 1)[0].strip()


def parse_config(text: str) -> dict[str, Any]:
    """Parse a live_docs config into a nested dict (tables become sub-dicts)."""
    if _toml_backend is not None:
        return _toml_backend.loads(text)

    # Fallback parser: flat top-level keys plus dotted tables (`[user]`,
    # `[store.<name>]`), each nested under its path.
    root: dict[str, Any] = {}
    section: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        parsed = _parse_value(val)
        if section is None:
            root[key] = parsed
            continue
        cur = root
        for part in section.split("."):
            part = part.strip().strip('"').strip("'")
            nxt = cur.get(part)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[part] = nxt
            cur = nxt
        cur[key] = parsed
    return root


def store_keys_from_config(data: dict[str, Any]) -> dict[str, str]:
    """Extract flat store path keys, ignoring the [user] table."""
    out: dict[str, str] = {}
    for key in STORE_CONFIG_KEYS:
        val = data.get(key)
        if isinstance(val, str) and val:
            out[key] = val
    return out


def _load_parsed(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return parse_config(path.read_text(encoding="utf-8"))
    except ValueError as e:
        # tomllib/tomli raise TOMLDecodeError (a ValueError) on malformed input;
        # surface a clean, actionable error rather than a raw traceback.
        raise ConfigChainError(f"malformed config {path}: {e}") from e


def read_store_keys(path: Path) -> dict[str, str]:
    """Shallow read of store keys from one file (no store delegation)."""
    return store_keys_from_config(_load_parsed(path))


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _toml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def dump_config(data: dict[str, Any]) -> str:
    """Serialize flat store paths, the [user] table, and [store.*] registry.

    Root-level keys are emitted before any table (TOML requires it): flat store
    path fallbacks first, then `[user]`, then the `[store.<name>]` registry.
    """
    lines: list[str] = []

    store_present = [k for k in STORE_CONFIG_KEYS if isinstance(data.get(k), str) and data[k]]
    if store_present:
        lines.append("# Store paths — fallback when no .live_docs.toml is found in the CWD tree")
        for key in STORE_CONFIG_KEYS:
            val = data.get(key)
            if isinstance(val, str) and val:
                lines.append(f"{key} = {_toml_quote(val)}")

    user = data.get("user")
    user_fields: dict[str, str] = {}
    if isinstance(user, dict):
        for key in ("name", "email"):
            val = user.get(key)
            if isinstance(val, str) and val.strip():
                user_fields[key] = val.strip()
    if user_fields:
        if lines:
            lines.append("")
        lines.append("# User identity (default review sign-off — git author format)")
        lines.append("[user]")
        if "name" in user_fields:
            lines.append(f"name = {_toml_quote(user_fields['name'])}")
        if "email" in user_fields:
            lines.append(f"email = {_toml_quote(user_fields['email'])}")

    stores = data.get("store")
    entries: dict[str, dict[str, str]] = {}
    if isinstance(stores, dict):
        for name, entry in stores.items():
            if not isinstance(entry, dict):
                continue
            kept = {
                key: entry[key].strip()
                for key in ("root", "url", "remote_name")
                if isinstance(entry.get(key), str) and entry[key].strip()
            }
            if "root" in kept or "url" in kept:
                entries[name] = kept
    if entries:
        if lines:
            lines.append("")
        lines.append("# Registered stores — name -> location (per machine): a local")
        lines.append("# checkout, or the url of a host that serves it.")
        for name in sorted(entries):
            entry = entries[name]
            lines.append(f"[store.{name}]")
            for key in ("root", "url", "remote_name"):
                if key in entry:
                    lines.append(f"{key} = {_toml_quote(entry[key])}")

    return "\n".join(lines) + ("\n" if lines else "")


def read_config_file(path: Path) -> dict[str, Any]:
    return _load_parsed(path)


def write_config_file(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = dump_config(data)
    # Atomic write: the home config is shared (identity + registry) and is now
    # written on self-registration, so avoid torn reads under concurrency.
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
