"""
toml_flat.py — TOML read/write for live_docs config files.

Supports a `[user]` table (name, email) plus flat top-level store path keys.
Stdlib only; uses tomllib/tomli when available.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

STORE_KEYS = ("inbox", "raw", "docs", "reviews", "index")

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
    """Parse a live_docs config into a nested dict."""
    if _toml_backend is not None:
        return _toml_backend.loads(text)

    root: dict[str, Any] = {}
    user: dict[str, str] = {}
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
        if section == "user":
            user[key] = parsed
        else:
            root[key] = parsed
    if user:
        root["user"] = user
    return root


def store_keys_from_config(data: dict[str, Any]) -> dict[str, str]:
    """Extract flat store path keys, ignoring the [user] table."""
    out: dict[str, str] = {}
    for key in STORE_KEYS:
        val = data.get(key)
        if isinstance(val, str) and val:
            out[key] = val
    return out


def _load_parsed(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return parse_config(path.read_text(encoding="utf-8"))


def read_store_keys(path: Path) -> dict[str, str]:
    return store_keys_from_config(_load_parsed(path))


def _toml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def dump_config(data: dict[str, Any]) -> str:
    """Serialize [user] + store path keys in a stable layout."""
    lines: list[str] = []

    user = data.get("user")
    user_fields: dict[str, str] = {}
    if isinstance(user, dict):
        for key in ("name", "email"):
            val = user.get(key)
            if isinstance(val, str) and val.strip():
                user_fields[key] = val.strip()

    store_present = [k for k in STORE_KEYS if isinstance(data.get(k), str) and data[k]]

    if user_fields:
        if store_present:
            lines.append("# User identity (default review sign-off — git author format)")
        lines.append("[user]")
        if "name" in user_fields:
            lines.append(f"name = {_toml_quote(user_fields['name'])}")
        if "email" in user_fields:
            lines.append(f"email = {_toml_quote(user_fields['email'])}")
        if store_present:
            lines.append("")

    if store_present:
        lines.append("# Store paths — fallback when no .live_docs.toml is found in the CWD tree")
        for key in STORE_KEYS:
            val = data.get(key)
            if isinstance(val, str) and val:
                lines.append(f"{key} = {_toml_quote(val)}")

    return "\n".join(lines) + ("\n" if lines else "")


def read_config_file(path: Path) -> dict[str, Any]:
    return _load_parsed(path)


def write_config_file(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_config(data), encoding="utf-8")
