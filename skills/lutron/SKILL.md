---
name: lutron
description: |
  Control Lutron Caseta smart lighting: activate scenes, toggle Smart Away (vacation mode),
  list devices, areas, and occupancy groups, and turn individual fixtures off.
  Use when the user asks to:
  - Turn off a light, set the house to night mode, or leave/arrive home
  - Enable or disable vacation mode / Smart Away
  - List what lights, shades, or rooms are available
  - Check which rooms are occupied
  - Activate a programmed Lutron scene by name
---

# Lutron Caseta

Control a Lutron Caseta Smart Bridge (L-BDG2-WH and similar) via the `lutron` CLI.

## Prerequisites

1. Install the CLI: `pipx install lutron-cli`
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
| `lutron_turn_off` | Turn a device off, with optional `fade` seconds. |
| `lutron_away_status` | Current Smart Away state (`Enabled` / `Disabled`). |
| `lutron_away_on` | Enable Smart Away (simulates occupancy while away). |
| `lutron_away_off` | Disable Smart Away. |
| `lutron_areas` | List rooms/areas on the bridge. |
| `lutron_occupancy` | Occupancy sensor groups with `Occupied` / `Unoccupied` status. |

## Common workflows

**Leave Home**
```
lutron_scenes → find the scene named "Leave Home"
lutron_activate_scene { scene_id: "<id>" }
lutron_away_on
```

**Arrive Home**
```
lutron_away_off
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
lutron_turn_off { device_id: "<id>", fade: 3 }
```

## Output format

Every tool returns the JSON emitted by the CLI. On error the response is `{ "success": false, "error": "<message>" }` — when that message mentions ENOENT, the CLI isn't installed; instruct the user to run `pipx install lutron-cli`.

## Notes

- Device and scene ids are strings (e.g. `"3"`), not integers.
- Smart Away works regardless of whether any lights are currently on — it cycles them on a schedule to simulate occupancy.
- The CLI connects per invocation (~2–3s per call); batching is not needed but very rapid successive calls may queue.
