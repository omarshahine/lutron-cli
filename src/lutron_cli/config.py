"""Configuration file management for lutron-cli."""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "lutron-cli"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    """Load config from disk. Returns empty dict if missing."""
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text())


def save_config(data: dict) -> None:
    """Write config to disk, creating parent dirs as needed."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2) + "\n")


def get_default_host() -> str | None:
    """Return the configured default bridge host, or None."""
    return load_config().get("default_host")


def set_default_host(host: str) -> None:
    """Set the default bridge host."""
    cfg = load_config()
    cfg["default_host"] = host
    save_config(cfg)
