# livedocs-mcp

An MCP endpoint for [live_docs](../README.md): it answers Model Context Protocol
requests so a reader without a checkout — a person, or their agent — can orient
in and read an up-to-date store.

Its tools are the porcelain's **read** commands. Each tool carries a command's
name, its arguments and its semantics, and answers with the same data that
command's `--json` output carries, because both surfaces call the same shared
code. An agent that orients with `ldoc map`, searches with `ldoc find` and reads
with `ldoc show` already knows this surface. It exposes the read commands alone;
changes still travel through the CLI.

The endpoint serves the files of a checkout on its host and holds no copy of its
own. Keeping that checkout current belongs to the deployment, done the way any
other checkout is kept current — the endpoint re-reads a store's docs whenever
they change on disk, with no restart.

It is an optional part of the tool, the way git's web server is optional to git:
it is packaged here on its own with its own dependencies, and `ldoc` behaves the
same whether or not it is installed. The shared code it calls stays stdlib-only.

## Install and run

The endpoint reads the shared code out of the checkout it was installed from, so
install it **from a checkout** (`uv run` and `pip install -e` both do that).

```sh
# uv — no install step; run it straight from the checkout
uv run --directory server livedocs-mcp

# pip — editable install into an environment of your own
python3 -m pip install -e server
livedocs-mcp
```

## Flags and environment

| Flag | Default | What it does |
| --- | --- | --- |
| `--transport http\|stdio` | `http` | Streamable HTTP at `/mcp` (stateless, JSON responses), or stdio for a local client. |
| `--host` | `127.0.0.1` | Address to bind for HTTP. |
| `--port` | `8000` | Port to bind for HTTP. |
| `--store NAME` | — | Serve only this registered store. Repeatable. |
| `--root PATH` | — | Serve the store at this path, for a host with no registry. Repeatable. It answers under the `name` its `.live_docs.toml` declares, or its directory name. |
| `--allowed-host HOST[:PORT]` | — | Also answer requests whose `Host` header is this. Required when `--host` is not loopback. A value with no port stands for that name on any port. Repeatable. |

With no `--store` and no `--root`, every store in the host's per-user registry
(`ldoc store list`) is served. A registry name bound to a *url* is skipped with a
notice: that store lives on another host, and this endpoint serves checkouts
rather than proxying other endpoints. Each tool then takes an optional `store` argument
naming which one to read; it may be omitted when exactly one store is served.
Call `store_list` for the names.

`LIVEDOCS_MCP_TOKEN` sets the shared token (see below). It is never logged.

## Pointing a client at it

Over stdio, for a client that launches the process itself:

```json
{
  "mcpServers": {
    "live_docs": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/live_docs/server", "livedocs-mcp",
               "--transport", "stdio"]
    }
  }
}
```

Over HTTP, point a streamable-HTTP client at `http://<host>:<port>/mcp` and have
it send `Authorization: Bearer <token>` when a token is configured.

Tools whose answer is not itself an object — a list, or a single string — return
it as structured content under a `result` key, which is how MCP requires a
structured answer to be an object; tools whose answer is already an object return
it directly.

## Security stance

The endpoint answers only requests carrying the shared token it is configured
with, given as `LIVEDOCS_MCP_TOKEN` and sent as `Authorization: Bearer <token>`.
This is network hygiene: the token check is an affordance for the deployment's
security practices, not an auth system, and the network boundary — who can reach
the host at all — is the deployment's.

Requests are also accepted only for `Host` headers the endpoint knows — the
loopback names for the bound port, plus every `--allowed-host` — and any request
carrying an `Origin` is refused. That is what keeps a web page from reading a
loopback endpoint through a name it controls, so binding off loopback needs
`--allowed-host` naming the host clients actually reach. Because that is the whole of the story,
binding anything other than loopback with no token set is refused at startup:
either set a token, or bind loopback and put a proxy that terminates TLS and
authenticates in front of it. stdio ignores the token; the client already owns
the process. Every tool is read-only and hands the shared code no editing
session, so nothing a request carries can write to a store.
