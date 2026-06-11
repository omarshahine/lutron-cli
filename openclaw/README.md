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

## Safety & privacy

This plugin controls physical devices in your home, so it ships with guardrails:

- **Kill switch confirmation.** `lutron_all_off` turns off the entire home at once. By default it requires an interactive confirmation before it fires, and it is **blocked in headless/automation contexts** (where there is no UI to confirm) unless you explicitly opt in with `allowUnattended`. Prefer a scoped `area` over the whole house.
- **Prompt-injection guardrails.** Every state-changing tool tells the agent to act only on a direct request from you, and never on instructions buried in untrusted content (emails, web pages, documents, calendar invites).
- **Occupancy is private.** `lutron_occupancy` and `lutron_export` reveal whether people are home and the full layout of the house. The tools flag this to the agent as sensitive; results should not be forwarded to third parties or untrusted channels.
- **No shell injection.** The plugin invokes the `lutron` binary with an argv array (never a shell string), so device names and ids cannot inject shell metacharacters.

Tune the gating with the config keys below. For an extra-cautious setup, set `confirmStateChanges: true` to require a confirmation before *every* change, not just the kill switch.

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `cliPath` | `lutron` | Path to the `lutron` binary |
| `bridgeHost` | (CLI config) | Bridge IP or hostname, overrides the lutron-cli saved config |
| `confirmAllOff` | `true` | Require an interactive confirmation before `lutron_all_off` fires |
| `confirmStateChanges` | `false` | Require confirmation before *every* state-changing tool, not just the kill switch |
| `allowUnattended` | `false` | Permit confirmation-gated actions to run when no interactive UI is available (trusted automation only) |

## Tips

- Prefer scenes over individual device control. One scene activation is faster than setting ten devices one by one (each call carries bridge connection overhead).
- Device and scene IDs are strings. Always pass them as strings.
- `lutron_set_level` is the single tool for on/off/dim. There is no separate on/off tool: `level: 0` turns off, `level: 100` is full on.

## License

MIT (c) Omar Shahine
