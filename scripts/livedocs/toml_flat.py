"""
toml_flat.py — TOML read/write for live_docs config files.

Supports a `[user]` table (name, email), flat top-level store path keys, and a
per-user store registry of `[store.<name>]` tables (name -> local checkout).
Stdlib only; uses tomllib/tomli when available, else a small fallback parser.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._paths import CONFIG_FILENAME, HOME_CONFIG

STORE_KEYS = ("inbox", "raw", "docs", "reviews", "sessions", "index")
BOX_KEYS = ("inbox", "raw", "docs", "reviews", "sessions")
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
}


class ConfigChainError(Exception):
    """Invalid store-delegation chain or unreadable config file."""


@dataclass
class StoreResolution:
    """Resolved store settings from a discovered ``.live_docs.toml``."""

    config: dict[str, str]
    sources: dict[str, Path]
    store_root: Path
    consumer_root: Path | None
    consumer_locals: dict[str, str] = field(default_factory=dict)
    store_name: str | None = None


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
# Per-user store registry (name -> local checkout), in the home config
# ---------------------------------------------------------------------------

def _looks_like_path(value: str) -> bool:
    """A ``store`` value is a path (vs a registered name) when it has path syntax."""
    return "/" in value or "\\" in value or value.startswith("~") or value.startswith(".")


def read_store_registry(home_config: Path = HOME_CONFIG) -> dict[str, str]:
    """Return {store_name: root} from the home config's ``[store.*]`` tables."""
    stores = _load_parsed(home_config).get("store")
    out: dict[str, str] = {}
    if isinstance(stores, dict):
        for name, entry in stores.items():
            if isinstance(entry, dict):
                root = entry.get("root")
                if isinstance(root, str) and root.strip():
                    out[name] = root.strip()
    return out


def resolve_store_name(name: str, home_config: Path = HOME_CONFIG) -> Path | None:
    """Look ``name`` up in the registry; return its (unchecked) root, or None."""
    root = read_store_registry(home_config).get(name)
    return Path(root).expanduser().resolve() if root else None


def set_store_registry_entry(
    home_config: Path, name: str, root: Path, *, force: bool = False,
) -> tuple[str, str | None]:
    """Upsert ``name`` -> ``root`` in the registry.

    Returns ``(status, existing_root)`` where status is ``added`` | ``unchanged``
    | ``updated`` | ``conflict``. On ``conflict`` (the name is already bound to a
    different path and ``force`` is False) nothing is written — the caller decides
    whether to fail loud or re-run with force.
    """
    data = read_config_file(home_config)
    stores = data.get("store")
    if not isinstance(stores, dict):
        stores = {}
    new_root = str(Path(root).expanduser().resolve())
    entry = stores.get(name)
    old_root = entry.get("root") if isinstance(entry, dict) else None
    if isinstance(old_root, str) and old_root.strip():
        if str(Path(old_root).expanduser().resolve()) == new_root:
            return ("unchanged", old_root)
        if not force:
            return ("conflict", old_root)
        status = "updated"
    else:
        status = "added"
    stores[name] = {"root": new_root}
    data["store"] = stores
    write_config_file(home_config, data)
    return (status, old_root)


def remove_store_registry_entry(home_config: Path, name: str) -> bool:
    """Drop ``name`` from the registry. Returns True if it was present."""
    data = read_config_file(home_config)
    stores = data.get("store")
    if isinstance(stores, dict) and name in stores:
        del stores[name]
        if stores:
            data["store"] = stores
        else:
            data.pop("store", None)
        write_config_file(home_config, data)
        return True
    return False


# ---------------------------------------------------------------------------
# Store delegation resolution
# ---------------------------------------------------------------------------

def _resolve_config_ref(value: str, from_dir: Path) -> Path:
    """Resolve a path-form ``store`` target — a file path or a directory holding one."""
    p = Path(value).expanduser()
    if not p.is_absolute():
        p = from_dir / p
    p = p.resolve()
    if p.is_dir():
        p = p / CONFIG_FILENAME
    return p


def _resolve_delegate(value: str, from_dir: Path, home_config: Path) -> Path:
    """Resolve a ``store`` value (a path or a registered name) to a config file.

    Fails loud with actionable messages when a name is unregistered or is
    registered to a location that no longer holds a store.
    """
    if _looks_like_path(value):
        target = _resolve_config_ref(value, from_dir)
        if not target.is_file():
            raise ConfigChainError(f"store path target not found: {target}")
        return target
    root = resolve_store_name(value, home_config)
    if root is None:
        raise ConfigChainError(
            f"store '{value}' is not registered. Register it by running "
            f"'ldoc store register' inside the store's checkout, or "
            f"'ldoc store register <path-to-store>'."
        )
    cfg = root / CONFIG_FILENAME
    if not cfg.is_file():
        raise ConfigChainError(
            f"store '{value}' is registered to {root}, which is missing or is not "
            f"a live_docs store. Re-register with "
            f"'ldoc store register --force <path-to-store>'."
        )
    return cfg


def _delegate_target(data: dict[str, Any]) -> str | None:
    raw = data.get(STORE_KEY)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _consumer_locals(data: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in CONSUMER_KEYS:
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            out[key] = val.strip()
    return out


def _load_terminal_store(
    config_path: Path,
    *,
    _seen: set[Path] | None = None,
    home_config: Path = HOME_CONFIG,
) -> tuple[dict[str, str], dict[str, Path], Path, str | None]:
    """Follow ``store`` delegation to the terminal store and load ITS keys.

    Delegation is a pointer, not inheritance: a file that carries a ``store``
    key is not a store, so its own path keys are ignored and resolution
    continues at the target (a path, or a registered name resolved through the
    per-user registry). Only the terminal config — the first one with no
    ``store`` key — contributes ``base`` + box paths, its declared ``name``, and
    the store root. Pointer chains are followed transitively; cycles raise.
    """
    config_path = config_path.resolve()
    seen = _seen if _seen is not None else set()
    if config_path in seen:
        chain = " -> ".join(str(p) for p in (*seen, config_path))
        raise ConfigChainError(f"circular store delegation: {chain}")
    seen.add(config_path)

    try:
        data = _load_parsed(config_path)
    except OSError as e:
        raise ConfigChainError(f"could not read config {config_path}: {e}") from e

    delegate_val = _delegate_target(data)
    if delegate_val:
        target = _resolve_delegate(delegate_val, config_path.parent, home_config)
        return _load_terminal_store(target, _seen=seen, home_config=home_config)

    merged: dict[str, str] = {}
    sources: dict[str, Path] = {}
    here = config_path.parent
    for key in STORE_CONFIG_KEYS:
        val = data.get(key)
        if isinstance(val, str) and val.strip():
            merged[key] = val.strip()
            sources[key] = here
    name_val = data.get(NAME_KEY)
    store_name = name_val.strip() if isinstance(name_val, str) and name_val.strip() else None
    return merged, sources, here.resolve(), store_name


def resolve_store_config(
    discovered_path: Path, *, home_config: Path = HOME_CONFIG,
) -> StoreResolution:
    """Resolve settings from the discovered ``.live_docs.toml``.

    When the discovered file sets ``store``, **all store path keys on that file
    are ignored** — the marker only points at an external store (by path or by
    registered name), and resolution follows the pointer to the terminal store.
    ``store_name`` is the terminal store's declared name (used for
    self-registration when the discovered file *is* that store).
    """
    discovered_path = discovered_path.resolve()
    try:
        data = _load_parsed(discovered_path)
    except OSError as e:
        raise ConfigChainError(f"could not read config {discovered_path}: {e}") from e

    consumer_root = discovered_path.parent
    consumer_locals = _consumer_locals(data)
    config, sources, store_root, store_name = _load_terminal_store(
        discovered_path, home_config=home_config,
    )
    return StoreResolution(
        config=config,
        sources=sources,
        store_root=store_root,
        consumer_root=consumer_root,
        consumer_locals=consumer_locals,
        store_name=store_name,
    )


def load_merged_store_config(
    config_path: Path,
    *,
    _seen: set[Path] | None = None,
) -> tuple[dict[str, str], dict[str, Path]]:
    """Backward-compatible wrapper around :func:`resolve_store_config`."""
    del _seen
    resolved = resolve_store_config(config_path)
    return resolved.config, resolved.sources


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
    entries: dict[str, str] = {}
    if isinstance(stores, dict):
        for name, entry in stores.items():
            if (isinstance(entry, dict)
                    and isinstance(entry.get("root"), str)
                    and entry["root"].strip()):
                entries[name] = entry["root"].strip()
    if entries:
        if lines:
            lines.append("")
        lines.append("# Registered stores — name -> local checkout (per machine)")
        for name in sorted(entries):
            lines.append(f"[store.{name}]")
            lines.append(f"root = {_toml_quote(entries[name])}")

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
