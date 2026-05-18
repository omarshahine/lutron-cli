# lutron-cli

Python CLI wrapping `pylutron-caseta` for Lutron Caseta smart lighting control.

## Project Structure

```
src/lutron_cli/
  __init__.py    # Version
  main.py        # Click CLI group + all subcommands
  config.py      # Config file CRUD (~/.config/lutron-cli/config.json)
  bridge.py      # Smartbridge connection helper + cert resolution
```

## Development

```bash
pip install -e .           # Install in editable mode
lutron --help              # Verify installation
lutron scan                # Test bridge discovery
```

## Key Patterns

- **Click groups**: `away` is a group with `invoke_without_command=True` so `lutron away` shows status while `lutron away on`/`off` are subcommands.
- **Connect-per-invocation**: Each command creates a fresh Smartbridge connection. ~2-3s per call. No daemon.
- **Cert reuse**: Reads certs from `~/.config/pylutron_caseta/` (standard pylutron-caseta location).
- **JSON output**: All commands output JSON to stdout. User-facing messages go to stderr.

## Dependencies

- `pylutron-caseta` - LEAP protocol, Smart Away, scene activation
- `click` - CLI framework
- `zeroconf` - mDNS bridge discovery
- `xdg` - XDG config path resolution

## Clawpatch Code Review

This repo uses [Clawpatch](https://clawpatch.ai) for local automated code review. Keep `.clawpatch/` ignored; it is generated runtime state containing features, findings, reports, runs, and patch attempts.

Standard workflow:

```bash
clawpatch doctor
clawpatch init          # first time only
clawpatch map
clawpatch review --limit 10
clawpatch report --output .clawpatch/reports/summary.md
clawpatch show --finding <id>
clawpatch fix --finding <id>
clawpatch revalidate --finding <id>
```

If this repo needs hand-authored feature coverage, keep those curated definitions in `tools/clawpatch/features/` and sync/copy them into `.clawpatch/features/` before review. Do not commit `.clawpatch/` generated state.
