"""Smoke tests for the Click CLI surface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from lutron_cli import config as config_module
from lutron_cli.main import cli

EXPECTED_COMMANDS = {
    "all",
    "areas",
    "away",
    "battery",
    "buttons",
    "config",
    "cover",
    "devices",
    "export",
    "fan",
    "info",
    "level",
    "occupancy",
    "off",
    "on",
    "pair",
    "scan",
    "scene",
    "scenes",
    "status",
    "tap",
    "warm",
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


@pytest.mark.parametrize(
    "argv",
    [
        ["on", "--help"],
        ["level", "--help"],
        ["fan", "--help"],
        ["cover", "--help"],
        ["warm", "--help"],
        ["buttons", "--help"],
        ["tap", "--help"],
        ["battery", "--help"],
        ["all", "--help"],
        ["info", "--help"],
        ["export", "--help"],
    ],
)
def test_new_commands_help(argv: list[str]) -> None:
    """Every new Phase 1/2/4 command should render its --help cleanly."""
    result = CliRunner().invoke(cli, argv)
    assert result.exit_code == 0, result.output
    assert "Usage:" in result.output


def test_all_requires_action() -> None:
    """`lutron all` with no action should fail cleanly, not crash."""
    result = CliRunner().invoke(cli, ["--host", "1.2.3.4", "all"])
    assert result.exit_code != 0


def test_all_rejects_unknown_action() -> None:
    """Only 'off' is valid today — 'on' should be rejected at parse time."""
    result = CliRunner().invoke(cli, ["--host", "1.2.3.4", "all", "on"])
    assert result.exit_code != 0
    assert "Invalid value" in result.output or "'on'" in result.output


def test_level_rejects_out_of_range() -> None:
    """Client-side guardrail: level must be 0..100."""
    result = CliRunner().invoke(cli, ["--host", "1.2.3.4", "level", "5", "200"])
    assert result.exit_code != 0
    assert "between 0 and 100" in result.output


def test_on_rejects_level_zero() -> None:
    """`on --level 0` should be rejected; use `off` instead."""
    result = CliRunner().invoke(cli, ["--host", "1.2.3.4", "on", "5", "--level", "0"])
    assert result.exit_code != 0
    assert "between 1 and 100" in result.output or "off" in result.output.lower()


def test_on_rejects_level_over_100() -> None:
    result = CliRunner().invoke(cli, ["--host", "1.2.3.4", "on", "5", "--level", "150"])
    assert result.exit_code != 0


def test_cover_action_is_case_insensitive() -> None:
    """Accept 'UP' / 'Up' / 'up' before we even hit bridge connection."""
    # Missing certs should be the failure mode, not Click arg parsing.
    result = CliRunner().invoke(cli, ["--host", "1.2.3.4", "cover", "5", "UP"])
    assert "Invalid value" not in result.output


def test_fan_rejects_unknown_speed() -> None:
    result = CliRunner().invoke(cli, ["--host", "1.2.3.4", "fan", "5", "turbo"])
    assert result.exit_code != 0
    assert "Invalid value" in result.output or "'turbo'" in result.output
