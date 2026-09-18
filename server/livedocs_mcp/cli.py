"""
cli.py — start the live_docs MCP endpoint.

Owns the process: flags, the startup checks that must fail loud, and the choice
of transport. Everything a request can go wrong with belongs to the tools, which
answer with an error rather than ending the process.
"""

from __future__ import annotations

import argparse
import ipaddress
import os
import sys

from . import shared  # noqa: F401  — puts the shared code on sys.path
from .auth import BearerToken
# The CLI client that reads a url-located store names this variable; both ends
# of the same token must agree on where it is read from.
from livedocs.endpoint_client import TOKEN_ENV_VAR
from .stores import StoreSet, select_stores
from .tools import register_tools

DESCRIPTION = (
    "Serve a host's live_docs stores over the Model Context Protocol. The tools "
    "are the porcelain's read commands, answering with the same data as "
    "`ldoc <command> --json`."
)

INSTRUCTIONS = (
    "Read-only access to one or more live_docs knowledge stores. Orient with "
    "`map`, search with `find`, read a doc with `show` or `body`, and walk the "
    "dependency graph with `neighbors` or `graph`. Every ref argument accepts an "
    "id, a label, a title, or a unique substring of either. Call `store_list` "
    "for the stores this endpoint serves."
)


_LOOPBACK_NAMES = ("127.0.0.1", "localhost", "[::1]")


def _is_loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host == "localhost"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="livedocs-mcp", description=DESCRIPTION)
    p.add_argument("--transport", default="http", choices=["http", "stdio"],
                   help="How clients reach the endpoint (default: http).")
    p.add_argument("--host", default="127.0.0.1",
                   help="Address to bind for --transport http (default: 127.0.0.1).")
    p.add_argument("--port", type=int, default=8000,
                   help="Port to bind for --transport http (default: 8000).")
    p.add_argument("--store", action="append", default=[], metavar="NAME",
                   help="Serve only this registered store. Repeatable.")
    p.add_argument("--root", action="append", default=[], metavar="PATH",
                   help="Serve the store at this path, for a host with no registry. "
                        "Repeatable.")
    p.add_argument("--allowed-host", action="append", default=[], metavar="HOST[:PORT]",
                   dest="allowed_hosts",
                   help="Accept requests whose Host header is this. Required when "
                        "--host is not loopback; name the host clients reach (a "
                        "proxy's public name). Repeatable.")
    return p


def _allowed_hosts(host: str, port: int, declared: "list[str]") -> "list[str]":
    """The Host header values this endpoint will answer to.

    A service that answers to any Host header can be reached by a web page that
    points a name it controls at this address, so the set is closed: the loopback
    names for the bound port, plus whatever the operator declared. A declared
    name with no port stands for that name on any port, since the name is what is
    being trusted.
    """
    allowed = [f"{h}:{port}" for h in _LOOPBACK_NAMES] + list(_LOOPBACK_NAMES)
    for value in declared:
        allowed.append(value)
        if ":" not in value:
            allowed.append(f"{value}:*")
    return allowed


def _require_allowed_host_off_loopback(host: str, declared: "list[str]") -> None:
    """Off loopback, make the operator say which name clients reach it by.

    Guessing is not possible: the address bound says nothing about the name a
    proxy or a DNS record puts in front of it, and a wrong guess either blocks
    every client or reopens the hole.
    """
    if declared or _is_loopback(host):
        return
    raise SystemExit(
        f"livedocs-mcp: refusing to bind {host} without --allowed-host.\n"
        f"Requests are accepted only for Host headers this endpoint knows, which is "
        f"what keeps a web page from reaching it through a name it controls. Name the "
        f"host clients use:\n"
        f"  --allowed-host docs.example.com          (any port on that name)\n"
        f"  --allowed-host docs.example.com:443      (that port only)"
    )


def _require_token_off_loopback(host: str, token: str) -> None:
    """Refuse to publish a store to a network with no token at all.

    Binding beyond loopback is a decision to let other machines read the store;
    with no token that decision is silent, so make the operator state it.
    """
    if token or _is_loopback(host):
        return
    raise SystemExit(
        f"livedocs-mcp: refusing to bind {host} with no {TOKEN_ENV_VAR} set.\n"
        f"Off loopback the endpoint is readable by anything that can reach the host. "
        f"Either:\n"
        f"  - set {TOKEN_ENV_VAR}=<shared token> and have clients send "
        f"'Authorization: Bearer <token>', or\n"
        f"  - bind loopback (--host 127.0.0.1) and put a proxy that terminates TLS and "
        f"authenticates in front of it."
    )


def _serve_http(server, host: str, port: int, token: str, allowed: "list[str]") -> None:
    import uvicorn
    from mcp.server.transport_security import TransportSecuritySettings

    app = server.streamable_http_app(
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
        host=host,
        # allowed_origins stays empty: a real MCP client sends no Origin, and a
        # browser page always does, so an empty list refuses the browser case
        # outright.
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed,
            allowed_origins=[],
        ),
    )
    if token:
        app = BearerToken(app, token)
    uvicorn.run(app, host=host, port=port, log_level="info")


def main(argv: "list[str] | None" = None) -> int:
    from mcp.server.mcpserver import MCPServer

    args = build_parser().parse_args(argv)
    token = os.environ.get(TOKEN_ENV_VAR, "").strip()

    if args.transport == "http":
        _require_token_off_loopback(args.host, token)
        _require_allowed_host_off_loopback(args.host, args.allowed_hosts)

    stores = StoreSet(select_stores(args.store, args.root))
    server = MCPServer(name="live_docs", title="live_docs",
                       description=DESCRIPTION, instructions=INSTRUCTIONS)
    tools = register_tools(server, stores)

    sys.stderr.write(
        f"livedocs-mcp: serving {len(stores.names)} store(s) "
        f"[{', '.join(stores.names)}] as {len(tools)} read-only tool(s)\n"
    )
    if args.transport == "stdio":
        server.run(transport="stdio")
        return 0

    sys.stderr.write(
        f"livedocs-mcp: http://{args.host}:{args.port}/mcp  "
        f"(token {'required' if token else 'not set'})\n"
    )
    _serve_http(server, args.host, args.port, token,
                _allowed_hosts(args.host, args.port, args.allowed_hosts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
