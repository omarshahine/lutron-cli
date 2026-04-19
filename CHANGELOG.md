# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-18

### Added
- `lutron` CLI with commands: `scan`, `pair`, `config`, `devices`, `status`,
  `off`, `scenes`, `scene`, `away` (with `on`/`off` subcommands), `areas`,
  `occupancy`.
- JSON-everywhere output, suitable for programmatic consumption.
- Connect-per-invocation model with cert reuse from the standard
  `~/.config/pylutron_caseta/` location.
- OpenClaw plugin (`openclaw-lutron` on npm, `lutron-caseta` on ClawHub) that
  shells out to the `lutron` binary and exposes one tool per CLI command.
- Install via `pipx install git+https://github.com/omarshahine/lutron-cli`
  (not distributed on PyPI).
- Claude Code plugin manifest (`lutron-caseta`) with a top-level `lutron`
  skill mirroring the OpenClaw skill.

### Fixed
- `lutron scan` crashed on zeroconf ≥ 0.38 because the `ServiceStateChange`
  callback is invoked with `zeroconf=` as a keyword argument. Renamed the
  callback parameter from `zc` to `zeroconf`.

[Unreleased]: https://github.com/omarshahine/lutron-cli/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/omarshahine/lutron-cli/releases/tag/v0.1.0
