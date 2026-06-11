# Lutron Caseta

OpenClaw plugin for Lutron Caseta smart lighting. It shells out to the `lutron` CLI to control lights, dimmers, shades, fans, and Pico remotes, activate scenes, toggle Smart Away vacation mode, and read occupancy, battery, and bridge health. Talks to a Lutron Caseta Smart Bridge on your local network.

## Install

1. Install the plugin from ClawHub.
2. Install the CLI it depends on:

   ```bash
   pipx install git+https://github.com/omarshahine/lutron-cli
   ```

   (Homebrew: `brew install omarshahine/tap/lutron-cli`.) Requires Python 3.10+.

3. Pair with your bridge once (press the small black button on the back within 180s):

   ```bash
   lutron scan         # find the bridge IP
   lutron pair <ip>    # saves pairing certs
   lutron devices      # verify: should return a JSON array
   ```

The plugin resolves the CLI from the `cliPath` config, the `LUTRON_CLI_PATH` env var, or `PATH`.

## Tools

| Tool | Purpose |
|------|---------|
| `lutron_scenes` | List programmed scenes (id + name). Call first to look up scene ids. |
| `lutron_activate_scene` | Activate a scene by `scene_id`. |
| `lutron_devices` | List paired devices. Optional `domain` filter: `light`, `switch`, `fan`, `cover`, `sensor`. |
| `lutron_device_status` | Current state of one device by `device_id`. |
| `lutron_set_level` | Set a light/dimmer/switch to `level` 0-100 (0 = off, 100 = full). Optional `fade` seconds. |
| `lutron_set_fan` | Set fan speed: `Off`, `Low`, `Medium`, `MediumHigh`, `High`. |
| `lutron_cover` | Raise, lower, or stop a shade/blind. Optional `tilt` 0-100. |
| `lutron_warm_dim` | Set warm-dim `level` on a warm-dim-capable bulb. |
| `lutron_buttons` | List Pico / keypad buttons (optional `device_id` filter). |
| `lutron_tap` | Simulate a Pico / keypad button press by `button_id`. |
| `lutron_battery` | Battery status for one device, or all battery-powered devices. |
| `lutron_smart_away` | Check, enable, or disable Smart Away (`action: status\|on\|off`). |
| `lutron_areas` | List rooms / areas on the bridge. |
| `lutron_occupancy` | Occupancy sensor groups (`Occupied` / `Unoccupied`). |
| `lutron_all_off` | Panic switch: turn off every controllable device. Optional `area`, `exclude`, `fade`. |
| `lutron_info` | Bridge health: connection state, device/scene/area counts, versions. |
| `lutron_export` | Full JSON snapshot of areas, devices, scenes, occupancy, buttons. |

## Smart Away

Smart Away randomly activates lights based on learned occupancy patterns to make it look like someone is home. It only works on Caseta Smart Bridges (not RA3 or HomeWorks QSX). Typical departure flow: activate a departure scene, `lutron_all_off` for anything left on, then `lutron_smart_away { action: "on" }`. Reverse on arrival.

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `cliPath` | `lutron` | Path to the `lutron` binary |
| `bridgeHost` | (CLI config) | Bridge IP or hostname, overrides the lutron-cli saved config |

## Tips

- Prefer scenes over individual device control. One scene activation is faster than setting ten devices one by one (each call carries bridge connection overhead).
- Device and scene IDs are strings. Always pass them as strings.
- `lutron_set_level` is the single tool for on/off/dim. There is no separate on/off tool: `level: 0` turns off, `level: 100` is full on.

## License

MIT (c) Omar Shahine
