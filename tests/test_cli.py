"""Smoke tests for the Click CLI surface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from lutron_cli import config as config_module
from lutron_cli.main import cli

EXPECTED_COMMANDS = {
    "areas",
    "away",
    "config",
    "devices",
    "occupancy",
    "off",
    "pair",
    "scan",
    "scene",
    "scenes",
    "status",
}


def test_help_lists_every_command() -> None:
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    for command in EXPECTED_COMMANDS:
        assert command in result.output, f"missing {command!r} in --help output"


def test_config_on_empty_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path / "lutron-cli")
    monkeypatch.setattr(
        config_module, "CONFIG_FILE", tmp_path / "lutron-cli" / "config.json"
    )

    result = CliRunner().invoke(cli, ["config"])
    assert result.exit_code == 0
    assert json.loads(result.output) == {"default_host": None}


def test_config_set_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path / "lutron-cli")
    monkeypatch.setattr(
        config_module, "CONFIG_FILE", tmp_path / "lutron-cli" / "config.json"
    )

    result = CliRunner().invoke(cli, ["config", "--host", "10.0.0.5"])
    assert result.exit_code == 0
    assert json.loads(result.output) == {"default_host": "10.0.0.5", "updated": True}
    assert config_module.get_default_host() == "10.0.0.5"


def test_devices_without_host_fails_clearly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path / "lutron-cli")
    monkeypatch.setattr(
        config_module, "CONFIG_FILE", tmp_path / "lutron-cli" / "config.json"
    )

    result = CliRunner().invoke(cli, ["devices"])
    assert result.exit_code != 0
    assert "No bridge host" in result.output
