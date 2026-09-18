"""
stores.py — which stores this endpoint answers for, and opening one per request.

The endpoint serves checkouts on its host and holds no copy: every request
re-opens the store it names and takes a KB that is reloaded only when that
store's files changed. Nothing here caches a store's resolved layout, so a
config edit or a moved checkout is picked up without a restart.
"""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from . import shared  # noqa: F401  — puts the shared code on sys.path
from livedocs._paths import HOME_CONFIG
from livedocs.kb import KB, KBCache
from livedocs.lexicon import LexiconStore
from livedocs.reviews import ReviewLedger
from livedocs.store import (
    LivedocsConfigError,
    StorePaths,
    open_store,
    read_store_registry,
)

# The classes whose reads this endpoint publishes, in the order their tools are
# registered. Each one declares its own READ_METHODS; this list is only which
# classes are served.
READ_OWNERS = (KB, LexiconStore, ReviewLedger)


@dataclass(frozen=True)
class ServedStore:
    """One store this endpoint answers for, with its layout already resolved.

    ``name`` is what callers ask for: the registry name for a registered store,
    and the store's declared (or directory) name for one given by path.
    """

    name: str
    paths: StorePaths


class StoreSet:
    """The stores this endpoint serves, and the KB cache shared across requests.

    Each store's layout is resolved once, at startup: a config chain does not
    change under a running endpoint, so re-walking it per request would pay for
    that on every read. What does change is the docs themselves, which the KB
    cache re-reads when they do.
    """

    def __init__(self, served: "list[ServedStore]") -> None:
        self._served = {s.name: s.paths for s in served}
        self._cache = KBCache()

    @property
    def names(self) -> "list[str]":
        return sorted(self._served)

    def reader(self, owner: type, name: "str | None"):
        """Open the named store and return the instance of ``owner`` that reads it.

        With a single store served the name is optional, because there is nothing
        to disambiguate. Otherwise a missing or unknown name is a caller error
        that names the alternatives.
        """
        paths = self._resolve(name)
        if not paths.docs.is_dir():
            # The checkout went away while the endpoint was up: say so the way
            # any other unusable store is said, rather than failing on the read.
            raise LivedocsConfigError(
                f"store '{name or self.names[0]}' is no longer readable: "
                f"{paths.docs} is missing. Restore the checkout on the host, or "
                f"restart the endpoint without it."
            )
        kb = self._cache.get(paths.docs)
        if owner is KB:
            return kb
        if owner is LexiconStore:
            return LexiconStore(paths.lexicon)
        # The KB already holds the store parsed, and a read creates nothing.
        return ReviewLedger(
            reviews_dir=paths.reviews, docs_dir=paths.docs,
            docs=kb.all_docs(), create=False,
        )

    def reachable(self, name: str) -> bool:
        """Whether the named store's docs are on disk right now."""
        return self._served[name].docs.is_dir()

    def _resolve(self, name: "str | None") -> StorePaths:
        """The resolved layout of the store a request names."""
        if name is None or not name.strip():
            if len(self._served) == 1:
                return next(iter(self._served.values()))
            raise LookupError(
                f"this endpoint serves {len(self._served)} stores — name the one you "
                f"mean with the 'store' argument: {', '.join(self.names)}"
            )
        paths = self._served.get(name.strip())
        if paths is None:
            raise LookupError(
                f"unknown store {name.strip()!r}. This endpoint serves: "
                f"{', '.join(self.names)}"
            )
        return paths


def _registry_names() -> "list[str]":
    """The store names this host can serve from its per-user registry.

    A name bound to a url points at some other host; serving it would make this
    endpoint a proxy, which is not what it is, so it is skipped and said aloud
    rather than failing at the first request for it.
    """
    names = []
    for name, entry in sorted(read_store_registry(HOME_CONFIG).items()):
        if entry.is_remote:
            sys.stderr.write(
                f"livedocs-mcp: skipping store '{name}' — it is registered to "
                f"a url ({entry.url}), and this endpoint serves checkouts on "
                f"this host, not other endpoints.\n"
            )
            continue
        names.append(name)
    return names


def _served_by_path(raw: str) -> ServedStore:
    """The store at a path, under the name it declares or its directory's."""
    root = Path(raw).expanduser().resolve()
    paths = open_store(str(root))
    return ServedStore(name=paths.store_name or root.name, paths=paths)


def select_stores(store_names: "list[str]", roots: "list[str]") -> "list[ServedStore]":
    """Decide the served set from the flags, failing loud when it would be empty.

    Named stores and paths combine; with neither, the whole registry is served,
    which is the plain "run it on the host that holds the checkouts" case.
    """
    served: list[ServedStore] = []

    for raw in roots:
        served.append(_served_by_path(raw))

    registry = _registry_names()
    if store_names:
        unknown = [n for n in store_names if n not in registry]
        if unknown:
            known = ", ".join(registry) if registry else "(none registered)"
            raise SystemExit(
                f"livedocs-mcp: --store named {', '.join(repr(n) for n in unknown)}, "
                f"which this host's registry does not bind.\n"
                f"Registered stores: {known}\n"
                f"Register one with 'ldoc store register <path-to-store>', or serve it "
                f"by path with --root <path-to-store>."
            )
        served.extend(ServedStore(name=n, paths=open_store(n)) for n in store_names)
    elif not roots:
        served.extend(ServedStore(name=n, paths=open_store(n)) for n in registry)

    if not served:
        raise SystemExit(
            "livedocs-mcp: no stores to serve — this host's registry is empty and no "
            "--root was given.\n"
            "Register a store with 'ldoc store register <path-to-store>', or serve one "
            "directly with --root <path-to-store>."
        )

    duplicates = sorted(n for n, c in Counter(s.name for s in served).items() if c > 1)
    if duplicates:
        raise SystemExit(
            f"livedocs-mcp: more than one served store answers to "
            f"{', '.join(repr(d) for d in duplicates)}.\n"
            f"Serve them one at a time, or give each store a distinct 'name' in its "
            f".live_docs.toml."
        )
    return served
