"""
store.py — where a store is, and opening it.

Everything between "a name or a directory" and "a store's resolved boxes": the
per-user registry that binds a name to a location, the delegation chain a
consumer marker points down, config discovery from a starting directory, and the
StorePaths value the rest of the tooling works from.

Nothing here knows what a doc is; nothing that knows what a doc is needs to know
any of this.

Stdlib only. No external dependencies.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._paths import CONFIG_FILENAME, HOME_CONFIG
from .toml_flat import (
    BASE_DEFAULT_SUBDIRS,
    BOX_KEYS,
    CONSUMER_KEYS,
    NAME_KEY,
    STORE_CONFIG_KEYS,
    STORE_KEY,
    ConfigChainError,
    _load_parsed,
    read_config_file,
    write_config_file,
)


class LivedocsConfigError(Exception):
    """No live_docs config could be located by discovery."""


class StoreNotRegisteredError(LivedocsConfigError):
    """A store was asked for by a name the per-user registry does not bind.

    Distinct from StoreUnreachableError because the remedies differ: this one is
    fixed by registering the name, not by repairing a checkout.
    """


class StoreUnreachableError(LivedocsConfigError):
    """A store's location is known but holds no readable store."""


# ---------------------------------------------------------------------------
# Per-user store registry (name -> location), in the home config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StoreEntry:
    """One ``[store.<name>]`` binding: exactly one location, plus its extras.

    A location is a local ``root`` or a ``url``; the two are alternatives, so a
    reader can ask which kind it got instead of guessing from the string.
    """

    name: str
    root: str | None = None
    url: str | None = None
    remote_name: str | None = None

    @property
    def is_remote(self) -> bool:
        return self.url is not None

    @property
    def location(self) -> str:
        return self.url if self.url is not None else (self.root or "")

    @property
    def served_as(self) -> str:
        """The name the host serves a url-bound store under.

        The local name is the default, so only a host that calls the store
        something else has to say so.
        """
        return self.remote_name or self.name


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def _looks_like_path(value: str) -> bool:
    """A ``store`` value is a path (vs a registered name) when it has path syntax."""
    return "/" in value or "\\" in value or value.startswith("~") or value.startswith(".")


def read_store_registry(home_config: Path = HOME_CONFIG) -> dict[str, StoreEntry]:
    """Return {store_name: StoreEntry} from the home config's ``[store.*]`` tables.

    An entry carrying neither location is dropped rather than half-read: a name
    bound to nothing is not a binding.
    """
    stores = _load_parsed(home_config).get("store")
    out: dict[str, StoreEntry] = {}
    if not isinstance(stores, dict):
        return out
    for name, entry in stores.items():
        if not isinstance(entry, dict):
            continue
        root, url = _text(entry.get("root")), _text(entry.get("url"))
        if not root and not url:
            continue
        out[name] = StoreEntry(
            name=name,
            root=root or None,
            # A url location wins if both are somehow present: the file was
            # hand-edited into a shape `ldoc store register` never writes.
            url=url or None,
            remote_name=_text(entry.get("remote_name")) or None,
        )
    return out


def store_entry(name: str, home_config: Path = HOME_CONFIG) -> StoreEntry | None:
    """Look ``name`` up in the registry, or None when nothing binds it."""
    return read_store_registry(home_config).get(name)


def normalize_store_url(value: str) -> str:
    """Validate a url location. Only http(s) addresses can be read over MCP."""
    url = (value or "").strip()
    scheme = url.split("://", 1)[0].lower() if "://" in url else ""
    if scheme not in ("http", "https"):
        raise ConfigChainError(
            f"{value!r} is not a usable store url — give the endpoint's http or "
            f"https address, e.g. https://docs.example.com/mcp"
        )
    return url


def set_store_registry_entry(
    home_config: Path,
    name: str,
    *,
    root: Path | None = None,
    url: str | None = None,
    remote_name: str | None = None,
    force: bool = False,
) -> tuple[str, str | None]:
    """Upsert ``name`` -> a location (a local ``root`` or a ``url``).

    Returns ``(status, existing_location)`` where status is ``added`` |
    ``unchanged`` | ``updated`` | ``conflict``. On ``conflict`` (the name is
    already bound somewhere else and ``force`` is False) nothing is written — the
    caller decides whether to fail loud or re-run with force. A rebind across
    kinds (root -> url or back) is a conflict like any other, because the name a
    consumer committed would start resolving somewhere new.
    """
    if (root is None) == (url is None):
        raise ValueError("a store entry is bound to exactly one of root or url")

    data = read_config_file(home_config)
    stores = data.get("store")
    if not isinstance(stores, dict):
        stores = {}

    if url is not None:
        new_entry: dict[str, str] = {"url": normalize_store_url(url)}
        if remote_name and remote_name != name:
            new_entry["remote_name"] = remote_name
        new_location = new_entry["url"]
    else:
        new_entry = {"root": str(Path(root).expanduser().resolve())}
        new_location = new_entry["root"]

    existing = read_store_registry(home_config).get(name)
    old_location = existing.location if existing else None
    if existing:
        same = (
            existing.url == new_entry.get("url")
            and (existing.remote_name or name) == (new_entry.get("remote_name") or name)
            and existing.root == new_entry.get("root")
        )
        if same:
            return ("unchanged", old_location)
        if not force:
            return ("conflict", old_location)
        status = "updated"
    else:
        status = "added"

    stores[name] = new_entry
    data["store"] = stores
    write_config_file(home_config, data)
    return (status, old_location)


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

@dataclass
class StoreResolution:
    """Resolved store settings from a discovered ``.live_docs.toml``."""

    config: dict[str, str] = field(default_factory=dict)
    sources: dict[str, Path] = field(default_factory=dict)
    store_root: Path = field(default_factory=Path)
    consumer_root: Path = field(default_factory=Path)
    consumer_locals: dict[str, str] = field(default_factory=dict)
    store_name: str | None = None


@dataclass(frozen=True)
class TerminalStore:
    """What following a config chain to its end produced."""

    config: dict[str, str]
    sources: dict[str, Path]
    root: Path
    store_name: str | None


def _resolve_config_ref(value: str, from_dir: Path) -> Path:
    """Resolve a path-form ``store`` target — a file path or a directory holding one."""
    p = Path(value).expanduser()
    if not p.is_absolute():
        p = from_dir / p
    p = p.resolve()
    if p.is_dir():
        p = p / CONFIG_FILENAME
    return p


def registered_store(
    name: str,
    home_config: Path = HOME_CONFIG,
    *,
    unbound: type = ConfigChainError,
    unusable: type = ConfigChainError,
) -> "Path | StoreEntry":
    """Resolve a registered name to its url binding, or to its config file.

    A registered name is a reference; where it leads is per-machine. It may lead
    to a checkout (a config file to keep resolving) or to a url (nothing local to
    resolve — the caller reads through the host). The two failures take their
    exception class from the caller, which is the only thing that differs between
    resolving a consumer marker and opening a store by name.
    """
    entry = store_entry(name, home_config)
    if entry is None:
        raise unbound(
            f"store '{name}' is not registered. Register it by running "
            f"'ldoc store register' inside the store's checkout, "
            f"'ldoc store register <path-to-store>', or "
            f"'ldoc store register {name} --url <endpoint-url>'."
        )
    if entry.is_remote:
        return entry
    root = Path(entry.root).expanduser().resolve()
    cfg = root / CONFIG_FILENAME
    if not cfg.is_file():
        raise unusable(
            f"store '{name}' is registered to {root}, which is missing or is not "
            f"a live_docs store. Re-register with "
            f"'ldoc store register --force <path-to-store>'."
        )
    return cfg


def _resolve_delegate(
    value: str, from_dir: Path, home_config: Path,
) -> "Path | StoreEntry":
    """Resolve a ``store`` value — a path, or a registered name — to its target."""
    if _looks_like_path(value):
        target = _resolve_config_ref(value, from_dir)
        if not target.is_file():
            raise ConfigChainError(f"store path target not found: {target}")
        return target
    return registered_store(value, home_config)


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
) -> "TerminalStore | StoreEntry":
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
        if isinstance(target, StoreEntry):
            return target
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
    return TerminalStore(merged, sources, here.resolve(), store_name)


def resolve_store_config(
    discovered_path: Path, *, home_config: Path = HOME_CONFIG,
) -> "StoreResolution | StoreEntry":
    """Resolve settings from the discovered ``.live_docs.toml``.

    Returns the registry entry itself when the chain ends at a name bound to a
    url: there is no terminal store on this machine to resolve paths against.

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

    terminal = _load_terminal_store(discovered_path, home_config=home_config)
    if isinstance(terminal, StoreEntry):
        return terminal
    return StoreResolution(
        config=terminal.config,
        sources=terminal.sources,
        store_root=terminal.root,
        consumer_root=discovered_path.parent,
        consumer_locals=_consumer_locals(data),
        store_name=terminal.store_name,
    )


# ---------------------------------------------------------------------------
# Discovery — a store is located by walking up, not by where this code lives
# ---------------------------------------------------------------------------
#
# A single installed `ldoc` must operate on whichever store the directory you're
# standing in belongs to, so resolution is anchored to a STARTING DIRECTORY, not
# to __file__. Git-style: walk up from that directory looking for a
# `.live_docs.toml` marker; if none is found there or in any parent, fall back
# to a per-user config at ~/.config/live_docs/config.toml; if neither exists,
# raise.
#
# The starting directory is the caller's to choose: the CLI passes its working
# directory, while a surface serving several stores in one process opens each by
# name or path (see open_store). Resolution never ends the process — failure is
# a LivedocsConfigError the surface decides what to do with.
#
# Paths inside a config file resolve relative to the directory CONTAINING that
# file (absolute and ~ paths are kept as-is). So a config can point at docs that
# live in a different repo entirely — a shared "mono-doc" store for several
# related code repos.

# Built-in defaults when neither `base` nor an explicit box key is set. Relative
# to the discovered config file's directory.
_DEFAULT_PATHS = {
    "docs": "docs",
    "raw": "raw",
    "reviews": "reviews",
    "sessions": "sessions",
    "lexicon": "lexicon",
    "inbox": "inbox",
    "index": None,  # None → derived as <docs>/.index
}

# Per-key env var overrides (win over the config file). Relative values resolve
# against the CWD, since they are invocation-time overrides.
_ENV_VARS = {
    "docs": "LIVEDOCS_DOCS_DIR",
    "raw": "LIVEDOCS_RAW_DIR",
    "reviews": "LIVEDOCS_REVIEWS_DIR",
    "sessions": "LIVEDOCS_SESSIONS_DIR",
    "lexicon": "LIVEDOCS_LEXICON_DIR",
    "inbox": "LIVEDOCS_INBOX_DIR",
}


@dataclass(frozen=True)
class StorePaths:
    """Every directory one store resolves to.

    Holding a store's layout in a value means a caller can work with several
    stores at once; the module-level constants below are one of these, fixed to
    the process's working directory.
    """

    store_root: Path
    consumer_root: "Path | None"
    consumer_locals: dict
    # The portable name the store declares for itself, when it declares one. A
    # caller that opened the store by path still needs it to say which store
    # this is.
    store_name: "str | None"
    docs: Path
    raw: Path
    reviews: Path
    sessions: Path
    lexicon: Path
    inbox: Path
    index: Path


def _find_config(start: Path) -> "tuple[Path | None, list[Path]]":
    """Locate the governing config file, walking up from ``start``.

    Returns (config_path, searched): the chosen file (or None if none exists)
    and every location inspected, so a failure can show its work.
    """
    searched: list[Path] = []
    cwd = Path(start).resolve()
    for d in (cwd, *cwd.parents):
        candidate = d / CONFIG_FILENAME
        searched.append(candidate)
        if candidate.is_file():
            return candidate, searched
    searched.append(HOME_CONFIG)
    if HOME_CONFIG.is_file():
        return HOME_CONFIG, searched
    return None, searched


def _resolve_path(value: str, base: Path) -> Path:
    """Resolve a configured path string relative to `base` (absolute/~ kept as-is)."""
    p = Path(value).expanduser()
    return p if p.is_absolute() else (base / p)


def _self_register_store(name: str, root: Path) -> None:
    """Idempotently record name -> root in the per-user registry.

    Never overwrites a conflicting binding and never raises: registration is a
    courtesy side-effect, so on a conflict it warns and moves on rather than
    blocking the command the user actually ran.
    """
    try:
        status, old = set_store_registry_entry(HOME_CONFIG, name, root=root, force=False)
    except OSError:
        return
    if status == "conflict":
        sys.stderr.write(
            f"ldoc: store name '{name}' is already registered to {old}, not {root}.\n"
            f"      Auto-registration skipped. If this checkout is the right one, run: "
            f"ldoc store register --force\n"
        )


def _resolve(start: Path, *, self_register: bool) -> "StorePaths | StoreEntry":
    """Run discovery from ``start`` and resolve every store directory.

    ``self_register`` records the store's declared name in the per-user registry;
    only the working-directory discovery path does that, because standing inside
    a checkout is what makes the binding mean "this one".
    """
    config_path, searched = _find_config(start)
    cwd = Path(start).resolve()

    if config_path is None:
        # Escape hatch: explicit env overrides can operate without a marker file
        # (e.g. CI). Otherwise there is no store to point at — complain.
        if not any(os.environ.get(v) for v in _ENV_VARS.values()):
            looked = "\n".join(f"  - {p}" for p in searched)
            raise LivedocsConfigError(
                f"no live_docs config found.\n"
                f"Looked for '{CONFIG_FILENAME}' in the current directory and each "
                f"parent, then for a home config:\n{looked}\n"
                f"Create a '{CONFIG_FILENAME}' at your store root, or set a "
                f"LIVEDOCS_* override."
            )
        store_root = cwd
        consumer_root = None
        config: dict[str, str] = {}
        sources: dict[str, Path] = {}
        consumer_locals: dict[str, str] = {}
        store_name: str | None = None
    else:
        try:
            store = resolve_store_config(config_path)
        except ConfigChainError as e:
            raise LivedocsConfigError(str(e)) from e
        if isinstance(store, StoreEntry):
            return store
        config = store.config
        sources = store.sources
        store_root = store.store_root
        consumer_root = store.consumer_root
        consumer_locals = store.consumer_locals
        store_name = store.store_name

        # When we are standing inside the store itself (the discovered marker is
        # that store, not a consumer pointer) and it declares a name, record
        # name -> root so consumers can resolve it. Idempotent; fail-loud on a
        # conflicting binding without blocking this command.
        if self_register and store.store_name and consumer_root == store_root:
            _self_register_store(store.store_name, store_root)

    base_path: Path | None = None
    if config.get("base"):
        base_source = sources.get("base", store_root)
        base_path = _resolve_path(config["base"], base_source)

    resolved: dict = {
        "store_root": store_root,
        "consumer_root": consumer_root,
        "consumer_locals": consumer_locals,
        "store_name": store_name,
    }
    for key in BOX_KEYS:
        env_val = os.environ.get(_ENV_VARS[key])
        if env_val:
            resolved[key] = _resolve_path(env_val, cwd)
        elif key in config:
            source = sources.get(key, store_root)
            resolved[key] = _resolve_path(config[key], source)
        elif base_path is not None:
            resolved[key] = base_path / BASE_DEFAULT_SUBDIRS[key]
        else:
            resolved[key] = store_root / _DEFAULT_PATHS[key]

    # Index cache derives under docs by default; an explicit `index` key
    # (config only — no env var) overrides it.
    if config.get("index"):
        index_source = sources.get("index", store_root)
        resolved["index"] = _resolve_path(config["index"], index_source)
    else:
        resolved["index"] = resolved["docs"] / ".index"
    return StorePaths(**resolved)


def open_store_at(start: Path) -> "StorePaths | StoreEntry":
    """Open the store the directory ``start`` belongs to.

    The discovery entry point: a surface that has a working directory (the CLI)
    uses this, and it is the only path that self-registers a named store.
    """
    return _resolve(Path(start), self_register=True)


def open_store(target: str) -> "StorePaths | StoreEntry":
    """Open a store named by the registry, or given as a filesystem path.

    For a surface that serves many stores from one process: the store comes from
    the request, so no working directory takes part and nothing is registered as
    a side effect of answering.
    """
    value = (target or "").strip()
    if not value:
        raise LivedocsConfigError(
            "no store given. Pass a registered store name (see: ldoc store list) "
            "or a path to a store's checkout."
        )

    if _looks_like_path(value):
        root = Path(value).expanduser().resolve()
        if root.is_file():
            root = root.parent
        if not (root / CONFIG_FILENAME).is_file():
            raise StoreUnreachableError(
                f"no live_docs store at {root} — expected a '{CONFIG_FILENAME}' "
                f"there. Pass the store's checkout, or register it and open it by "
                f"name: ldoc store register <path-to-store>."
            )
        return _resolve(root, self_register=False)

    target_or_entry = registered_store(
        value, HOME_CONFIG,
        unbound=StoreNotRegisteredError, unusable=StoreUnreachableError,
    )
    if isinstance(target_or_entry, StoreEntry):
        return target_or_entry
    return _resolve(target_or_entry.parent, self_register=False)


_resolved_store: "StorePaths | StoreEntry | None" = None

_PATH_ATTRS: dict[str, str] = {
    "STORE_ROOT": "store_root",
    "CONSUMER_ROOT": "consumer_root",
    "REPO_ROOT": "store_root",  # backward-compatible alias
    "DOCS_DIR": "docs",
    "RAW_DIR": "raw",
    "REVIEWS_DIR": "reviews",
    "SESSIONS_DIR": "sessions",
    "LEXICON_DIR": "lexicon",
    "INBOX_DIR": "inbox",
    "INDEX_DIR": "index",
}


def cwd_store() -> "StorePaths | StoreEntry":
    """The store the process's working directory belongs to, resolved once.

    This is the working-directory convenience the module constants are views on.
    Raises LivedocsConfigError rather than exiting: the surface that called in
    owns what a missing store means to its user.
    """
    global _resolved_store
    if _resolved_store is None:
        _resolved_store = open_store_at(Path.cwd())
    return _resolved_store


def __getattr__(name: str) -> "Path":
    if name in _PATH_ATTRS:
        store = cwd_store()
        if isinstance(store, StoreEntry):
            # The constants are directories; a url location has none. Reads go
            # through the host, and anything else has no local store to touch.
            raise LivedocsConfigError(
                f"store '{store.name}' is registered to a url ({store.url}), which "
                f"has no directories on this machine. Read it with `ldoc` "
                f"(read commands resolve through the host), or check it out and "
                f"bind the name to it: ldoc store register --force <path-to-store>"
            )
        obj = getattr(store, _PATH_ATTRS[name])
        globals()[name] = obj  # cache so subsequent access skips __getattr__
        return obj
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
