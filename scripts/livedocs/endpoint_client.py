"""
endpoint_client.py — read a store through the host serving it.

When a registered name is bound to a url, `ldoc` reads that store by acting as
an MCP client of the host: it calls the same tools an agent harness calls and
hands the answers back in the shape the local read path produces, so a read
command behaves the same for its caller whether the store is a directory or an
address.

A remote reader stands in for one of the reading classes — KB, LexiconStore,
ReviewLedger — and is built from that class's own READ_METHODS and signatures, so
there is no second list of reads here to keep in step with the first.

Stdlib only (urllib), because this sits in the shared code the CLI runs on. It
speaks the one request the endpoint's stateless streamable-HTTP transport needs
— a JSON-RPC POST — and nothing else.
"""

from __future__ import annotations

import inspect
import json
import os
import urllib.error
import urllib.request

from .store import LivedocsConfigError, StoreEntry, StoreUnreachableError

TOKEN_ENV_VAR = "LIVEDOCS_MCP_TOKEN"

# Long enough for a big `map` over a slow link, short enough that a wrong url
# fails while the caller is still watching.
TIMEOUT_SECONDS = 20

# The SDK wraps a tool's own failure message in this when a tool raises rather
# than answering. Stripping it back off is what lets a remote read fail with the
# message a local read would have printed.
_TOOL_ERROR_PREFIX = "Error executing tool "

# What a live_docs endpoint says a failure was, and what that means here. A store
# the host cannot resolve or does not serve is a store problem for this client
# too, and ends the same way an unresolvable store name does locally.
_ERROR_TYPES = {
    "config": LivedocsConfigError,
    "lookup": LivedocsConfigError,
    "value": ValueError,
}


def tool_name(namespace: str, method: str) -> str:
    """One reading class's method as a single tool name (`term` + `ls` -> `term_ls`).

    A tool name cannot carry a space, and two classes may both own a `show`, so
    the class's namespace goes in front of it. Defined here, beside the client
    that calls the tools, and read by the endpoint that publishes them, so both
    ends spell a name the same way.
    """
    return f"{namespace}_{method}" if namespace else method


def reader(store: StoreEntry, owner: type):
    """A stand-in for ``owner`` that answers its reads through the host.

    The returned object carries exactly ``owner.READ_METHODS``, each accepting
    what the real method accepts, so a caller handed one cannot tell it apart
    from the class itself — and anything the class can do besides read is simply
    absent, which is all that is legal against a read-only location.
    """
    return _RemoteReader(store, owner)


class _RemoteReader:
    """One reading class's read methods, forwarded to the host as tool calls."""

    def __init__(self, store: StoreEntry, owner: type) -> None:
        self._store = store
        self._owner = owner

    def __getattr__(self, name: str):
        if name not in self._owner.READ_METHODS:
            raise AttributeError(
                f"{self._owner.__name__} read surface has no attribute {name!r}"
            )
        method = getattr(self._owner, name)

        def call(*args, **kwargs):
            return _read(self._store, self._owner, name, _arguments(method, args, kwargs))

        return call


def _arguments(method, args: tuple, kwargs: dict) -> dict:
    """Bind a call against the real method's signature, minus ``self``.

    Binding against the method itself is what lets a caller pass positionally,
    by keyword, or not at all, exactly as it would locally. A value left at its
    default is not sent — the host applies the same default from the same
    signature.
    """
    signature = inspect.signature(method)
    without_self = signature.replace(
        parameters=list(signature.parameters.values())[1:]
    )
    bound = without_self.bind(*args, **kwargs)
    return {k: v for k, v in bound.arguments.items() if v is not None}


def _token() -> str:
    """The shared token, from the environment.

    Never from the registry: the registry is a per-user map of names to places,
    committed nowhere, but a secret in it would still be a secret written to a
    file that exists to be copied between machines.
    """
    return os.environ.get(TOKEN_ENV_VAR, "").strip()


def _unreachable(store: StoreEntry, detail: str, fix: str) -> StoreUnreachableError:
    return StoreUnreachableError(
        f"store '{store.name}' at {store.url} could not be read: {detail}\n{fix}"
    )


def _post(store: StoreEntry, payload: dict) -> dict:
    """POST one JSON-RPC request and return the parsed response object."""
    headers = {
        "content-type": "application/json",
        # The transport refuses a request that does not accept both, even in
        # stateless mode where it always answers with JSON.
        "accept": "application/json, text/event-stream",
    }
    token = _token()
    if token:
        headers["authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        store.url, data=json.dumps(payload).encode("utf-8"),
        method="POST", headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
            content_type = response.headers.get("content-type", "")
    except urllib.error.HTTPError as e:
        raise _http_error(store, e) from e
    except urllib.error.URLError as e:
        raise _unreachable(
            store, str(e.reason),
            "Check the url, that the host is running its endpoint, and that this "
            "machine can reach it.",
        ) from e
    except OSError as e:  # includes socket.timeout on a hung host
        raise _unreachable(
            store, str(e),
            f"The host did not answer within {TIMEOUT_SECONDS}s. Check that it is "
            f"running and reachable.",
        ) from e

    return _parse(store, body, content_type)


def _http_error(store: StoreEntry, e: urllib.error.HTTPError) -> StoreUnreachableError:
    if e.code == 401:
        return _unreachable(
            store, "the host rejected the request as unauthorized (401)",
            f"Set the shared token the host was started with: "
            f"export {TOKEN_ENV_VAR}=<token>",
        )
    if e.code == 421:
        return _unreachable(
            store, "the host refused the Host header (421)",
            "Reach it by a name the host was started to answer to (its "
            "--allowed-host), not by a bare address.",
        )
    return _unreachable(
        store, f"HTTP {e.code} {e.reason}",
        "Check that the url points at the endpoint's MCP path (it usually ends "
        "in /mcp).",
    )


def _parse(store: StoreEntry, body: str, content_type: str) -> dict:
    """Read a JSON-RPC response out of a JSON body, or a single-event SSE one.

    The endpoint answers with plain JSON, but the streamable-HTTP transport is
    allowed to answer with an event stream, so one event is understood too rather
    than failing on a deployment that turned JSON responses off.
    """
    text = body
    if "text/event-stream" in content_type.lower():
        text = ""
        for line in body.splitlines():
            if line.startswith("data:"):
                text = line[5:].strip()
                break
        if not text:
            raise _unreachable(
                store, "the host sent an event stream carrying no data event",
                "This endpoint is expected to answer with JSON; check its version.",
            )
    try:
        return json.loads(text)
    except ValueError as e:
        raise _unreachable(
            store, f"the host's answer was not JSON ({e})",
            "Check that the url points at an MCP endpoint and not at another "
            "service.",
        ) from e


def _read(store: StoreEntry, owner: type, method: str, arguments: dict):
    """Call one read on the host and return what the local method would return.

    Raises ValueError for a failure inside the read — an unresolvable ref, a bad
    pattern — carrying the host's own message, which is the message the local
    read would have printed. Everything about reaching the host at all raises
    StoreUnreachableError.
    """
    name = tool_name(owner.READ_NAMESPACE, method)
    response = _post(store, {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": dict(arguments, store=store.served_as)},
    })

    error = response.get("error")
    if error:
        raise _unreachable(
            store, f"the host rejected the request: {error.get('message', error)}",
            "Check that the host serves this store and runs a matching version "
            "of the endpoint.",
        )

    result = response.get("result") or {}
    structured = result.get("structuredContent")
    if result.get("isError"):
        raise _tool_failure(result, structured)

    if structured is None:
        raise _unreachable(
            store, f"the host returned no structured answer for '{name}'",
            "Check that the host runs a matching version of the endpoint.",
        )
    # A method answering with anything but a mapping is wrapped, because MCP
    # structured output must be an object.
    if isinstance(structured, dict) and set(structured) == {"result"}:
        return structured["result"]
    return structured


def _tool_failure(result: dict, structured) -> Exception:
    """The exception a local read would have raised for this failure.

    A live_docs endpoint names the kind; any other host, or an older one, only
    sends the SDK's wrapped text, so that is read as a plain command failure.
    """
    reported = (structured or {}).get("error") if isinstance(structured, dict) else None
    if isinstance(reported, dict) and reported.get("kind") in _ERROR_TYPES:
        return _ERROR_TYPES[reported["kind"]](reported.get("message", ""))

    text = " ".join(
        part.get("text", "") for part in result.get("content", [])
        if isinstance(part, dict)
    ).strip()
    if text.startswith(_TOOL_ERROR_PREFIX):
        _tool, _, message = text[len(_TOOL_ERROR_PREFIX):].partition(": ")
        return ValueError(message or text)
    return ValueError(text)
