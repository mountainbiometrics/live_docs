"""
tools.py — publish the reading classes' methods as MCP tools.

A tool is built from the method that answers it: its parameters, defaults and
enums come from the real signature, its description from the real docstring. A
read command is therefore defined once, in the class that owns it, and neither
the `ldoc` CLI nor this endpoint can drift from the other. Nothing here
enumerates commands by hand.
"""

from __future__ import annotations

import inspect
import typing
from typing import Any, Optional

from livedocs.endpoint_client import tool_name
from livedocs.store import LivedocsConfigError
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent, ToolAnnotations

from .stores import READ_OWNERS, StoreSet

_STORE_HELP = (
    "Which of the stores this endpoint serves to read. Optional when it serves "
    "exactly one; call store_list for the names."
)


def _store_parameter() -> inspect.Parameter:
    """The argument every tool takes and no method has: which store to read."""
    return inspect.Parameter(
        "store", inspect.Parameter.KEYWORD_ONLY,
        default=None, annotation=Optional[str],
    )


def _tool_function(method, name: str, impl):
    """A function whose signature is exactly the method's, plus `store`.

    The SDK derives a tool's schema from the signature, so building a real one
    out of the method is what lets the method define the wire contract with no
    per-command code to keep in step. ``get_type_hints`` resolves the string
    annotations the shared code writes under ``from __future__ import
    annotations``.
    """
    hints = typing.get_type_hints(method)
    signature = inspect.signature(method)
    params = [
        p.replace(
            kind=inspect.Parameter.KEYWORD_ONLY,
            annotation=hints.get(p.name, p.annotation),
        )
        # [1:] drops `self`: the endpoint supplies the instance, per request.
        for p in list(signature.parameters.values())[1:]
    ]
    params.append(_store_parameter())
    returns = hints["return"]

    def call(**kwargs):
        return impl(**kwargs)

    call.__name__ = name
    call.__doc__ = inspect.cleandoc(method.__doc__ or "")
    call.__signature__ = inspect.Signature(params, return_annotation=returns)
    call.__annotations__ = {p.name: p.annotation for p in params}
    call.__annotations__["return"] = returns
    return call


# What a failure was, in the caller's terms. A client that speaks live_docs can
# turn these back into the exception a local read would have raised, instead of
# reading it out of an error string.
_ERROR_KINDS = (
    (LivedocsConfigError, "config"),
    (LookupError, "lookup"),
    (ValueError, "value"),
)


def _answer(stores: StoreSet, owner: type, method: str, kwargs: dict) -> Any:
    """Run one read against the named store, turning expected failures into tool errors.

    Neither a store that cannot be opened nor a ref that does not resolve is the
    endpoint's to die of, so each comes back to the caller as the message the CLI
    would have printed, alongside the kind of failure it was.
    """
    store_name = kwargs.pop("store", None)
    try:
        return getattr(stores.reader(owner, store_name), method)(**kwargs)
    except tuple(cls for cls, _ in _ERROR_KINDS) as e:
        return _failed(e)


def _failed(e: Exception) -> CallToolResult:
    kind = next(name for cls, name in _ERROR_KINDS if isinstance(e, cls))
    return CallToolResult(
        content=[TextContent(type="text", text=str(e))],
        structuredContent={"error": {"kind": kind, "message": str(e)}},
        isError=True,
    )


def _register(server: MCPServer, fn, name: str, description: str) -> None:
    server.add_tool(
        fn,
        name=name,
        description=description,
        annotations=ToolAnnotations(read_only_hint=True),
        structured_output=True,
    )


def _register_store_list(server: MCPServer, stores: StoreSet) -> None:
    """The endpoint's own account of what it serves.

    Not a read of any store, and deliberately not the host's registry: a name a
    caller may pass, and whether asking about it right now would work, is all a
    remote caller has business knowing. Where a store sits on this host is the
    operator's.
    """
    def store_list() -> list[dict[str, Any]]:
        """List the stores this endpoint serves."""
        return [
            {"name": name, "reachable": stores.reachable(name)}
            for name in stores.names
        ]

    _register(server, store_list, "store_list", store_list.__doc__)


def register_tools(server: MCPServer, stores: StoreSet) -> "list[str]":
    """Register one read-only tool per read method of each reading class, plus
    store_list. Returns the tool names.
    """
    registered: list[str] = []
    for owner in READ_OWNERS:
        for method in owner.READ_METHODS:
            name = tool_name(owner.READ_NAMESPACE, method)
            fn = _tool_function(
                getattr(owner, method), name,
                (lambda o, m: lambda **kwargs: _answer(stores, o, m, kwargs))(owner, method),
            )
            _register(server, fn, name, fn.__doc__)
            registered.append(name)
    _register_store_list(server, stores)
    registered.append("store_list")
    return registered
