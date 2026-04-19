"""Tests for config file CRUD."""

from __future__ import annotations

from pathlib import Path

import pytest

from lutron_cli import config as config_module


@pytest.fixture
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect config reads/writes into a per-test tmp_path."""
    cfg_dir = tmp_path / "lutron-cli"
    cfg_file = cfg_dir / "config.json"
    monkeypatch.setattr(config_module, "CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", cfg_file)
    return cfg_file


def test_load_missing_config_returns_empty(isolated_config: Path) -> None:
    assert config_module.load_config() == {}


def test_save_and_load_roundtrip(isolated_config: Path) -> None:
    config_module.save_config({"default_host": "10.0.0.1", "other": 42})
    assert isolated_config.exists()
    assert config_module.load_config() == {"default_host": "10.0.0.1", "other": 42}


def test_set_and_get_default_host(isolated_config: Path) -> None:
    assert config_module.get_default_host() is None
    config_module.set_default_host("bridge.local")
    assert config_module.get_default_host() == "bridge.local"


def test_set_default_host_preserves_other_keys(isolated_config: Path) -> None:
    config_module.save_config({"other": "keep-me"})
    config_module.set_default_host("10.0.0.2")
    assert config_module.load_config() == {
        "other": "keep-me",
        "default_host": "10.0.0.2",
    }
