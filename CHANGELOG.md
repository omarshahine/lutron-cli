# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.12] - 2026-10-17

### Fixed
- The OpenClaw plugin build failed under TypeScript 7, which no longer loads
  `@types/node` by default, so 0.1.11 never reached npm or ClawHub.
  `openclaw/tsconfig.json` now lists `"types": ["node"]`, and CI builds the
  plugin on every PR.

## [0.1.11] - 2026-10-17

### Fixed
- Bridge connections hung forever on Python 3.13+ with "Reconnecting after
  error: check_hostname requires server_hostname". The TLS context now pins
  the bridge CA with hostname checking off, since the bridge cert isn't
  issued for its IP.

## [0.1.10] - 2026-06-11

### Added
- OpenClaw plugin safety guardrails in response to the ClawHub security audit:
  - `lutron_all_off` (whole-home kill switch) now requires an interactive
    confirmation by default and is blocked in headless/automation contexts
    unless explicitly opted in. New config keys: `confirmAllOff` (default
    true), `confirmStateChanges` (default false), `allowUnattended` (default
    false).
  - Every state-changing tool carries prompt guidelines instructing the agent
    to act only on direct user requests and never on instructions embedded in
    untrusted content (prompt-injection guardrail).
  - `lutron_occupancy` and `lutron_export` are flagged as privacy-sensitive
    (they reveal presence and home layout) with guidance not to expose results
    to untrusted channels.
- "Safety & privacy" documentation in the plugin README and skill.

## [0.1.8] - 2026-05-26

### Added
- `lutron area` command group with `list` / `rename` / `delete` / `create`
  subcommands. Uses the underlying LEAP primitives
  (`UpdateRequest`/`DeleteRequest`/`CreateRequest` against `/area/<id>` and
  `/area`) directly through `bridge._request()`.
- `lutron move <device_id> <area_id>` — reassign a device to a different
  area; the bridge recomputes `FullyQualifiedName` automatically.
- Safety guard: `area delete` refuses to delete a non-empty area unless
  `--force` is passed.
- All new write commands support `--dry-run`.

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

[Unreleased]: https://github.com/omarshahine/lutron-cli/compare/v0.1.12...HEAD
[0.1.12]: https://github.com/omarshahine/lutron-cli/compare/v0.1.11...v0.1.12
[0.1.11]: https://github.com/omarshahine/lutron-cli/compare/v0.1.10...v0.1.11
[0.1.8]: https://github.com/omarshahine/lutron-cli/releases/tag/v0.1.8
[0.1.0]: https://github.com/omarshahine/lutron-cli/releases/tag/v0.1.0
