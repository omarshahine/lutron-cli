# lutron-cli

CLI for Lutron Caseta smart lighting, with first-class support for scenes,
Smart Away (vacation mode), device inspection, and agent-friendly JSON output.
Ships with matching [OpenClaw](https://openclaw.ai) and
[Claude Code](https://claude.com/claude-code) plugins so AI agents can drive
it out of the box.

## Install

```bash
pipx install git+https://github.com/omarshahine/lutron-cli
```

Or for development:

```bash
git clone https://github.com/omarshahine/lutron-cli
cd lutron-cli
pip install -e ".[dev]"
```

Requires Python 3.10+ and a Lutron Caseta Smart Bridge on the same network.

## Setup

1. **Discover the bridge:**
   ```bash
   lutron scan
   ```
   Returns an array like `[{"name": "Lutron-…", "addresses": ["192.168.1.50"], "port": 22}]`.

2. **Pair** (press the small black button on the back of the bridge when prompted — 180-second window):
   ```bash
   lutron pair 192.168.1.50
   ```
   Certs are stored in `~/.config/pylutron_caseta/`; the bridge IP is stored as the default host in `~/.config/lutron-cli/config.json`.

3. **Verify:**
   ```bash
   lutron devices | head
   ```

## CLI Usage

Every command prints JSON to stdout; status messages go to stderr.

### Scenes

```bash
lutron scenes                 # list all programmed scenes
lutron scene 3                # activate scene by id
```

### Smart Away (vacation mode)

```bash
lutron away                   # status
lutron away on                # enable
lutron away off               # disable
```

### Devices

```bash
lutron devices                      # all devices
lutron devices --domain light       # only lights
lutron status 5                     # one device by id
lutron off 5                        # turn off device 5
lutron off 5 --fade 3               # turn off over 3s fade
lutron on 5                         # turn on device 5
lutron on 5 --level 60 --fade 2     # turn on to 60% over 2s
lutron level 5 30                   # set dimmer 5 to 30%
lutron level 5 30 --fade 2          # ...with 2s fade
```

### Fans, Shades, and Warm-Dim Bulbs

```bash
lutron fan 8 Medium                 # Off | Low | Medium | MediumHigh | High
lutron cover 12 down                # up | down | stop
lutron cover 12 up --tilt 45        # tiltable blind
lutron warm 7 20                    # warm-dim level (candle-style color shift)
lutron warm 7 20 --fade 3           # ...with fade
```

### Picos, Keypads, and Battery Status

```bash
lutron buttons                      # list every Pico/keypad button
lutron buttons --device 14          # filter to one Pico's buttons
lutron tap 42                       # simulate a button press by button_id
lutron battery                      # scan all battery-powered devices
lutron battery 14                   # battery for one device
```

### Areas & Occupancy

```bash
lutron areas                  # rooms/areas
lutron occupancy              # occupancy sensor groups with current status
```

### Bulk Operations

```bash
lutron all off                             # panic: turn off every light/switch/fan/cover
lutron all off --area "Kitchen"            # limit to one room
lutron all off --fade 3 --exclude 5,12     # graceful dim-down, spare 2 devices
```

### Health & Snapshot

```bash
lutron info                   # bridge connection, device counts, CLI + library versions
lutron export                 # full JSON snapshot: areas + devices + scenes + buttons
```

### Configuration

```bash
lutron config                         # show current default
lutron config --host 192.168.1.50     # set default bridge
lutron --host 10.0.0.8 devices        # override per-invocation
```

Config file: `~/.config/lutron-cli/config.json`.
Cert location: `~/.config/pylutron_caseta/`.

## AI Agent Plugins

### OpenClaw

```bash
openclaw plugins install lutron-caseta
```

Registers 17 tools: `lutron_scenes`, `lutron_activate_scene`, `lutron_devices`,
`lutron_device_status`, `lutron_set_level` (0-100; 0 = off, 100 = full on),
`lutron_set_fan`, `lutron_cover`, `lutron_warm_dim`, `lutron_buttons`,
`lutron_tap`, `lutron_battery`, `lutron_smart_away` (status/on/off),
`lutron_areas`, `lutron_occupancy`, `lutron_all_off` (panic switch),
`lutron_info` (health), `lutron_export` (snapshot).

The CLI itself keeps separate `on`, `off`, `level`, and `away on|off|status`
subcommands for human shell use — only the agent tool surface is consolidated.

The plugin shells out to the `lutron` binary, so install the CLI first with
`pipx install lutron-cli` and pair the bridge before installing the plugin.

### Claude Code

The plugin lives in the same repo under `.claude-plugin/` with a `lutron`
skill in `skills/lutron/SKILL.md`. Install via:

```bash
claude plugin install omarshahine/lutron-cli
```

## Troubleshooting

- **`lutron scan` returns `[]`** — mDNS is being blocked. Confirm the bridge
  is on the same Layer-2 segment as your machine, and that the firewall
  allows UDP port 5353. On macOS, briefly disable the firewall to test.
- **Pairing times out** — the bridge only accepts pairing for 180 seconds
  after you press the button. Start `lutron pair …` first, then press.
- **`certificate verify failed`** — the certs in `~/.config/pylutron_caseta/`
  don't match this bridge. Re-pair: `lutron pair <ip>`.
- **Wrong bridge** — use `--host` to override, or edit
  `~/.config/lutron-cli/config.json`.

## License

MIT — see [LICENSE](./LICENSE).
