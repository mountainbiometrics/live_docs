"""Shared path constants — no store discovery, no side effects at import time."""
from pathlib import Path

CONFIG_FILENAME = ".live_docs.toml"
HOME_CONFIG: Path = Path.home() / ".config" / "live_docs" / "config.toml"
