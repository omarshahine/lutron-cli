---
name: lutron
description: |
  Control Lutron Caseta smart lighting: activate scenes, toggle Smart Away (vacation mode),
  list devices, areas, and occupancy groups, turn fixtures on/off, set dimmer levels, control
  shades and fans, simulate Pico button presses, and check battery levels on Picos and sensors.
  Use when the user asks to:
  - Turn a light on or off, set a dimmer to a specific level
  - Raise, lower, or stop a shade or blind (with optional tilt)
  - Change fan speed on a Caseta fan controller
  - Enable or disable vacation mode / Smart Away
  - List what lights, shades, rooms, or Pico buttons are available
  - Check which rooms are occupied, or which Picos / sensors have low batteries
  - Activate a programmed Lutron scene by name
  - Simulate a Pico / keypad button press to fire its programmed action
---

# Lutron Caseta

Control a Lutron Caseta Smart Bridge (L-BDG2-WH and similar) via the `lutron` CLI.

## Prerequisites

1. Install the CLI: `pipx install git+https://github.com/omarshahine/lutron-cli`
2. Pair with the bridge once (requires pressing the small black button on its back):
   ```bash
   lutron scan         # find the bridge IP
   lutron pair <ip>    # saves certs; press the button within 180s
   ```
3. Verify: `lutron devices` should return a JSON array.

The plugin shells out to `lutron` for every call. Install path is resolved from the plugin's `cliPath` config, `LUTRON_CLI_PATH` env var, or `PATH`.

## Tools

| Tool | Purpose |
|------|---------|
| `lutron_scenes` | List programmed scenes (id + name). Always call this first to look up scene ids. |
| `lutron_activate_scene` | Activate a scene by `scene_id`. |
| `lutron_devices` | List every paired device. Optional `domain` filter: `light`, `switch`, `fan`, `cover`, `sensor`. |
| `lutron_device_status` | Get current state of one device by `device_id`. |
| `lutron_set_level` | Set a light, dimmer, or switch to `level` 0-100. **0 = off, 100 = full on, anything in between dims.** This is the single tool for on/off/dim. Optional `fade` seconds. |
| `lutron_set_fan` | Set fan speed: `Off`, `Low`, `Medium`, `MediumHigh`, `High`. |
| `lutron_cover` | Raise, lower, or stop a shade/blind. Optional `tilt` (0-100) for tiltable blinds. |
| `lutron_warm_dim` | Set warm-dim `level` on a warm-dim-capable bulb (candle-style color shift as it dims). |
| `lutron_buttons` | List Pico / keypad buttons. Optional `device_id` filter. Returns button ids for `lutron_tap`. |
| `lutron_tap` | Simulate a Pico / keypad button press by `button_id`. Fires whatever that button is programmed to do. |
| `lutron_battery` | Battery status for one device, or scans all battery-powered devices when `device_id` omitted. |
| `lutron_smart_away` | Check (default), enable, or disable Smart Away. Pass `action: status\|on\|off`. |
| `lutron_areas` | List rooms/areas on the bridge. |
| `lutron_occupancy` | Occupancy sensor groups with `Occupied` / `Unoccupied` status. |
| `lutron_all_off` | Panic switch: turn off every controllable device. Optional `area` name, `exclude` (comma ids), `fade` seconds. |
| `lutron_info` | Bridge health: connection state, device/scene/area counts, CLI + library versions. |
| `lutron_export` | Full JSON snapshot of areas, devices, scenes, occupancy groups, buttons. For backup or diffing. |

## Common workflows

**Leave Home**
```
lutron_scenes → find the scene named "Leave Home"
lutron_activate_scene { scene_id: "<id>" }
lutron_smart_away { action: "on" }
```

**Arrive Home**
```
lutron_smart_away { action: "off" }
lutron_scenes → find "Arrive Home"
lutron_activate_scene { scene_id: "<id>" }
```

**Is anyone home?**
```
lutron_occupancy → look at each group's status field
```

**Turn off a specific light over 3 seconds**
```
lutron_devices { domain: "light" } → find the device_id by name/area
lutron_set_level { device_id: "<id>", level: 0, fade: 3 }
```

**Turn a light fully on**
```
lutron_set_level { device_id: "<id>", level: 100 }
```

**Dim the living room to 30%**
```
lutron_devices { domain: "light" } → find the living room dimmer
lutron_set_level { device_id: "<id>", level: 30, fade: 2 }
```

**Lower the bedroom shades**
```
lutron_devices { domain: "cover" } → find the bedroom shade
lutron_cover { device_id: "<id>", action: "down" }
```

**Fire a Pico button remotely**
```
lutron_devices { domain: "sensor" } → find the Pico device_id
lutron_buttons { device_id: "<pico_id>" } → pick the button_number you want
lutron_tap { button_id: "<button_id>" }
```

**Low-battery sweep**
```
lutron_battery → returns every battery-powered device with its current level
```

**Kill every light in the house**
```
lutron_all_off { fade: 3 }                    # whole house, 3s fade
lutron_all_off { area: "Kitchen" }            # just one room
lutron_all_off { area: "Bedroom", exclude: "5" }   # all but one device
```

**Quick health check / backup**
```
lutron_info                                   # bridge + version summary
lutron_export                                 # full snapshot to stash or diff
```

## Output format

Every tool returns the JSON emitted by the CLI. On error the response is `{ "success": false, "error": "<message>" }` — when that message mentions ENOENT, the CLI isn't installed; instruct the user to run `pipx install lutron-cli`.

## Notes

- Device and scene ids are strings (e.g. `"3"`), not integers.
- Smart Away works regardless of whether any lights are currently on — it cycles them on a schedule to simulate occupancy.
- The CLI connects per invocation (~2–3s per call); batching is not needed but very rapid successive calls may queue.
