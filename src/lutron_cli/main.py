"""Lutron Caseta CLI - Click command group and all subcommands."""

from __future__ import annotations

import json
from datetime import timedelta

import click

from .bridge import get_cert_dir, get_cert_paths, open_bridge, run_async
from .config import get_default_host, load_config, set_default_host


def _json(data) -> None:
    """Print data as formatted JSON to stdout."""
    click.echo(json.dumps(data, indent=2, default=str))


def _resolve_host(host: str | None) -> str:
    """Resolve bridge host from argument or config, or fail."""
    if host:
        return host
    default = get_default_host()
    if default:
        return default
    raise click.ClickException(
        "No bridge host specified. Use --host or run 'lutron config --host <ip>'."
    )


@click.group()
@click.option("--host", default=None, help="Bridge IP address or hostname.")
@click.pass_context
def cli(ctx, host):
    """Lutron Caseta smart lighting CLI."""
    ctx.ensure_object(dict)
    ctx.obj["host"] = host


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------
@cli.command()
@click.option("--timeout", default=5, type=int, help="Discovery timeout in seconds.")
def scan(timeout):
    """Discover Lutron Caseta bridges on the local network via mDNS."""
    import socket

    from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf

    results = []

    def on_state_change(zeroconf, service_type, name, state_change):
        if state_change is ServiceStateChange.Added:
            info = zeroconf.get_service_info(service_type, name)
            if info:
                addresses = [
                    socket.inet_ntoa(addr) for addr in info.addresses
                ]
                results.append({
                    "name": info.server,
                    "addresses": addresses,
                    "port": info.port,
                })

    zc = Zeroconf()
    ServiceBrowser(zc, "_lutron._tcp.local.", handlers=[on_state_change])

    # Wait for discovery
    import time
    time.sleep(timeout)
    zc.close()

    _json(results)


# ---------------------------------------------------------------------------
# pair
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("host")
def pair(host):
    """Pair with a bridge. Press the small black button on the back when prompted."""

    async def _pair():
        from pylutron_caseta.pairing import async_pair

        click.echo(
            "Press the small black button on the back of the bridge within 180 seconds...",
            err=True,
        )
        data = await async_pair(host)

        # Save certs in the standard pylutron_caseta location
        cert_dir = get_cert_dir()
        cert_dir.mkdir(parents=True, exist_ok=True)

        key_path, cert_path, ca_path = get_cert_paths(host)
        key_path.write_text(data["key"])
        cert_path.write_text(data["cert"])
        ca_path.write_text(data["ca"])

        # Save as default host
        set_default_host(host)

        return {
            "success": True,
            "host": host,
            "version": data.get("version", "unknown"),
            "certs_dir": str(cert_dir),
        }

    result = run_async(_pair())
    _json(result)


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------
@cli.command()
@click.option("--host", "new_host", default=None, help="Set default bridge host.")
def config(new_host):
    """Show or set the default bridge configuration."""
    if new_host:
        set_default_host(new_host)
        _json({"default_host": new_host, "updated": True})
    else:
        cfg = load_config()
        if not cfg:
            cfg = {"default_host": None}
        _json(cfg)


# ---------------------------------------------------------------------------
# devices
# ---------------------------------------------------------------------------
@cli.command()
@click.option(
    "--domain",
    type=click.Choice(["light", "switch", "fan", "cover", "sensor"]),
    default=None,
    help="Filter devices by domain.",
)
@click.pass_context
def devices(ctx, domain):
    """List all devices connected to the bridge."""
    host = _resolve_host(ctx.obj["host"])

    async def _devices():
        async with open_bridge(host) as bridge:
            if domain:
                devs = bridge.get_devices_by_domain(domain)
            else:
                devs = bridge.get_devices()
                # get_devices returns a dict; convert values to list
                if isinstance(devs, dict):
                    devs = list(devs.values())
            return devs

    _json(run_async(_devices()))


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("device_id", required=False)
@click.pass_context
def status(ctx, device_id):
    """Get status of a specific device or all devices."""
    host = _resolve_host(ctx.obj["host"])

    async def _status():
        async with open_bridge(host) as bridge:
            if device_id:
                return bridge.get_device_by_id(device_id)
            else:
                devs = bridge.get_devices()
                return list(devs.values()) if isinstance(devs, dict) else devs

    _json(run_async(_status()))


# ---------------------------------------------------------------------------
# off
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("device_id")
@click.option("--fade", default=None, type=float, help="Fade time in seconds.")
@click.pass_context
def off(ctx, device_id, fade):
    """Turn off a device."""
    host = _resolve_host(ctx.obj["host"])

    async def _off():
        async with open_bridge(host) as bridge:
            if fade is not None:
                await bridge.set_value(
                    device_id, 0, fade_time=timedelta(seconds=fade)
                )
            else:
                await bridge.turn_off(device_id)
            return {"success": True, "device_id": device_id, "state": 0}

    _json(run_async(_off()))


# ---------------------------------------------------------------------------
# on
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("device_id")
@click.option("--level", default=None, type=int, help="Dimmer level 0-100 (default: full on).")
@click.option("--fade", default=None, type=float, help="Fade time in seconds.")
@click.pass_context
def on(ctx, device_id, level, fade):
    """Turn on a device, optionally at a specific level with fade."""
    if level is not None and not 0 <= level <= 100:
        raise click.BadParameter("--level must be between 0 and 100.")

    host = _resolve_host(ctx.obj["host"])

    async def _on():
        async with open_bridge(host) as bridge:
            if level is not None or fade is not None:
                await bridge.set_value(
                    device_id,
                    level if level is not None else 100,
                    fade_time=timedelta(seconds=fade) if fade is not None else None,
                )
            else:
                await bridge.turn_on(device_id)
            return {
                "success": True,
                "device_id": device_id,
                "state": level if level is not None else 100,
            }

    _json(run_async(_on()))


# ---------------------------------------------------------------------------
# level
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("device_id")
@click.argument("value", type=int)
@click.option("--fade", default=None, type=float, help="Fade time in seconds.")
@click.pass_context
def level(ctx, device_id, value, fade):
    """Set a dimmer to a specific level 0-100."""
    if not 0 <= value <= 100:
        raise click.BadParameter("level must be between 0 and 100.")

    host = _resolve_host(ctx.obj["host"])

    async def _level():
        async with open_bridge(host) as bridge:
            await bridge.set_value(
                device_id,
                value,
                fade_time=timedelta(seconds=fade) if fade is not None else None,
            )
            return {"success": True, "device_id": device_id, "state": value}

    _json(run_async(_level()))


# ---------------------------------------------------------------------------
# fan
# ---------------------------------------------------------------------------
FAN_SPEEDS = ["Off", "Low", "Medium", "MediumHigh", "High"]


@cli.command()
@click.argument("device_id")
@click.argument("speed", type=click.Choice(FAN_SPEEDS, case_sensitive=False))
@click.pass_context
def fan(ctx, device_id, speed):
    """Set fan speed: Off, Low, Medium, MediumHigh, or High."""
    # Normalize case to what the library expects.
    normalized = next(s for s in FAN_SPEEDS if s.lower() == speed.lower())

    host = _resolve_host(ctx.obj["host"])

    async def _fan():
        async with open_bridge(host) as bridge:
            await bridge.set_fan(device_id, normalized)
            return {"success": True, "device_id": device_id, "speed": normalized}

    _json(run_async(_fan()))


# ---------------------------------------------------------------------------
# cover (shades/blinds)
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("device_id")
@click.argument("action", type=click.Choice(["up", "down", "stop"], case_sensitive=False))
@click.option("--tilt", default=None, type=int, help="Tilt angle 0-100 (tiltable blinds only).")
@click.pass_context
def cover(ctx, device_id, action, tilt):
    """Control a shade or blind: up, down, or stop. Optional --tilt."""
    action = action.lower()
    if tilt is not None and not 0 <= tilt <= 100:
        raise click.BadParameter("--tilt must be between 0 and 100.")

    host = _resolve_host(ctx.obj["host"])

    async def _cover():
        async with open_bridge(host) as bridge:
            if action == "up":
                await bridge.raise_cover(device_id)
            elif action == "down":
                await bridge.lower_cover(device_id)
            else:
                await bridge.stop_cover(device_id)
            if tilt is not None:
                await bridge.set_tilt(device_id, tilt)
            return {
                "success": True,
                "device_id": device_id,
                "action": action,
                "tilt": tilt,
            }

    _json(run_async(_cover()))


# ---------------------------------------------------------------------------
# warm (warm-dim color-tuning bulbs)
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("device_id")
@click.argument("value", type=int)
@click.option("--fade", default=None, type=float, help="Fade time in seconds.")
@click.option(
    "--disable",
    is_flag=True,
    default=False,
    help="Disable warm-dim mode (keep level, restore normal dimming curve).",
)
@click.pass_context
def warm(ctx, device_id, value, fade, disable):
    """Set warm-dim level 0-100 on a warm-dim-capable bulb."""
    if not 0 <= value <= 100:
        raise click.BadParameter("value must be between 0 and 100.")

    host = _resolve_host(ctx.obj["host"])

    async def _warm():
        async with open_bridge(host) as bridge:
            await bridge.set_warm_dim(
                device_id,
                enabled=not disable,
                value=value,
                fade_time=timedelta(seconds=fade) if fade is not None else None,
            )
            return {
                "success": True,
                "device_id": device_id,
                "level": value,
                "warm_dim": not disable,
            }

    _json(run_async(_warm()))


# ---------------------------------------------------------------------------
# buttons
# ---------------------------------------------------------------------------
@cli.command()
@click.option(
    "--device",
    "device_id",
    default=None,
    help="Filter buttons belonging to a specific device (e.g. a Pico remote).",
)
@click.pass_context
def buttons(ctx, device_id):
    """List Pico / keypad buttons known to the bridge."""
    host = _resolve_host(ctx.obj["host"])

    async def _buttons():
        async with open_bridge(host) as bridge:
            b = bridge.get_buttons()
            items = list(b.values()) if isinstance(b, dict) else b
            if device_id:
                items = [
                    btn
                    for btn in items
                    if str(btn.get("parent_device")) == str(device_id)
                ]
            return items

    _json(run_async(_buttons()))


# ---------------------------------------------------------------------------
# tap
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("button_id")
@click.pass_context
def tap(ctx, button_id):
    """Simulate a Pico / keypad button press. Use `lutron buttons` to find ids."""
    host = _resolve_host(ctx.obj["host"])

    async def _tap():
        async with open_bridge(host) as bridge:
            await bridge.tap_button(button_id)
            return {"success": True, "button_id": button_id}

    _json(run_async(_tap()))


# ---------------------------------------------------------------------------
# battery
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("device_id", required=False)
@click.pass_context
def battery(ctx, device_id):
    """Get battery status for a device, or all battery-powered devices."""
    host = _resolve_host(ctx.obj["host"])

    async def _battery():
        async with open_bridge(host) as bridge:
            if device_id:
                status_val = await bridge.get_battery_status(device_id)
                return {"device_id": device_id, "battery_status": status_val}
            devs = bridge.get_devices()
            items = list(devs.values()) if isinstance(devs, dict) else devs
            results = []
            for dev in items:
                dev_id = dev.get("device_id") or dev.get("id")
                if not dev_id:
                    continue
                try:
                    status_val = await bridge.get_battery_status(dev_id)
                except Exception:  # noqa: BLE001 - library may raise for non-battery devices
                    continue
                if status_val is None:
                    continue
                results.append(
                    {
                        "device_id": dev_id,
                        "name": dev.get("name"),
                        "battery_status": status_val,
                    }
                )
            return results

    _json(run_async(_battery()))


# ---------------------------------------------------------------------------
# scenes
# ---------------------------------------------------------------------------
@cli.command()
@click.pass_context
def scenes(ctx):
    """List all programmed scenes on the bridge."""
    host = _resolve_host(ctx.obj["host"])

    async def _scenes():
        async with open_bridge(host) as bridge:
            s = bridge.get_scenes()
            return list(s.values()) if isinstance(s, dict) else s

    _json(run_async(_scenes()))


# ---------------------------------------------------------------------------
# scene
# ---------------------------------------------------------------------------
@cli.command()
@click.argument("scene_id")
@click.pass_context
def scene(ctx, scene_id):
    """Activate a scene by ID."""
    host = _resolve_host(ctx.obj["host"])

    async def _scene():
        async with open_bridge(host) as bridge:
            await bridge.activate_scene(scene_id)
            return {"success": True, "scene_id": scene_id}

    _json(run_async(_scene()))


# ---------------------------------------------------------------------------
# away (group with subcommands)
# ---------------------------------------------------------------------------
@cli.group(invoke_without_command=True)
@click.pass_context
def away(ctx):
    """Smart Away control. Run without subcommand to get status."""
    if ctx.invoked_subcommand is None:
        host = _resolve_host(ctx.obj["host"])

        async def _status():
            async with open_bridge(host) as bridge:
                state = await bridge.get_smart_away_status()
                return {"smart_away": state}

        _json(run_async(_status()))


@away.command("on")
@click.pass_context
def away_on(ctx):
    """Enable Smart Away mode (simulates occupancy while away)."""
    host = _resolve_host(ctx.parent.obj["host"])

    async def _on():
        async with open_bridge(host) as bridge:
            await bridge.activate_smart_away()
            state = await bridge.get_smart_away_status()
            return {"smart_away": state, "action": "enabled"}

    _json(run_async(_on()))


@away.command("off")
@click.pass_context
def away_off(ctx):
    """Disable Smart Away mode."""
    host = _resolve_host(ctx.parent.obj["host"])

    async def _off():
        async with open_bridge(host) as bridge:
            await bridge.deactivate_smart_away()
            state = await bridge.get_smart_away_status()
            return {"smart_away": state, "action": "disabled"}

    _json(run_async(_off()))


# ---------------------------------------------------------------------------
# areas
# ---------------------------------------------------------------------------
@cli.command()
@click.pass_context
def areas(ctx):
    """List all areas (rooms) configured on the bridge."""
    host = _resolve_host(ctx.obj["host"])

    async def _areas():
        async with open_bridge(host) as bridge:
            a = bridge.areas
            return list(a.values()) if isinstance(a, dict) else a

    _json(run_async(_areas()))


# ---------------------------------------------------------------------------
# occupancy
# ---------------------------------------------------------------------------
@cli.command()
@click.pass_context
def occupancy(ctx):
    """List occupancy groups with current status."""
    host = _resolve_host(ctx.obj["host"])

    async def _occupancy():
        async with open_bridge(host) as bridge:
            occ = bridge.occupancy_groups
            return list(occ.values()) if isinstance(occ, dict) else occ

    _json(run_async(_occupancy()))


# ---------------------------------------------------------------------------
# Phase 2: `all off` — panic switch for everything, optionally scoped to an area
# ---------------------------------------------------------------------------
CONTROLLABLE_DOMAINS = {"light", "switch", "fan", "cover"}


def _device_area_id(device: dict) -> str | None:
    """Return the area id for a device, accepting any of the shapes pylutron-caseta uses."""
    return (
        device.get("area")
        or device.get("area_id")
        or (device.get("parent_area") or {}).get("href")
    )


def _resolve_area_id(areas: dict, name: str) -> str | None:
    """Map an area name (case-insensitive) to its id."""
    for area_id, area in (areas or {}).items():
        if str(area.get("name", "")).lower() == name.lower():
            return area_id
    return None


@cli.command("all")
@click.argument("action", type=click.Choice(["off"], case_sensitive=False))
@click.option("--area", "area_name", default=None, help="Limit to devices in this area.")
@click.option("--fade", default=None, type=float, help="Fade time in seconds.")
@click.option(
    "--exclude",
    default=None,
    help="Comma-separated device ids to skip.",
)
@click.pass_context
def all_cmd(ctx, action, area_name, fade, exclude):
    """Bulk operation across many devices. Currently: 'all off' (panic switch)."""
    action = action.lower()
    exclude_ids = {s.strip() for s in exclude.split(",")} if exclude else set()

    host = _resolve_host(ctx.obj["host"])

    async def _all():
        async with open_bridge(host) as bridge:
            devs = bridge.get_devices()
            items = list(devs.values()) if isinstance(devs, dict) else devs

            target_area_id: str | None = None
            if area_name:
                target_area_id = _resolve_area_id(bridge.areas, area_name)
                if target_area_id is None:
                    raise click.ClickException(f"Area not found: {area_name!r}")

            affected: list[dict] = []
            skipped: list[dict] = []
            for dev in items:
                dev_id = str(dev.get("device_id") or dev.get("id") or "")
                if not dev_id:
                    continue
                domain = dev.get("domain") or dev.get("type")
                if domain and str(domain).lower() not in CONTROLLABLE_DOMAINS:
                    # Sensors, Picos, keypad LEDs etc.
                    continue
                if dev_id in exclude_ids:
                    skipped.append({"device_id": dev_id, "reason": "excluded"})
                    continue
                if target_area_id and _device_area_id(dev) != target_area_id:
                    continue
                try:
                    if fade is not None:
                        await bridge.set_value(
                            dev_id, 0, fade_time=timedelta(seconds=fade)
                        )
                    else:
                        await bridge.turn_off(dev_id)
                    affected.append({"device_id": dev_id, "name": dev.get("name")})
                except Exception as err:  # noqa: BLE001
                    skipped.append(
                        {"device_id": dev_id, "name": dev.get("name"), "error": str(err)}
                    )

            return {
                "action": action,
                "area": area_name,
                "fade": fade,
                "affected": affected,
                "skipped": skipped,
                "count": len(affected),
            }

    _json(run_async(_all()))


# ---------------------------------------------------------------------------
# Phase 4: info — bridge + library status
# ---------------------------------------------------------------------------
@cli.command()
@click.pass_context
def info(ctx):
    """Show bridge connection status, device/scene/area counts, and CLI version."""
    from importlib.metadata import version as pkg_version

    host = _resolve_host(ctx.obj["host"])

    async def _info():
        async with open_bridge(host) as bridge:
            devs = bridge.get_devices()
            scenes_map = bridge.get_scenes()
            areas_map = bridge.areas or {}
            return {
                "host": host,
                "connected": bool(bridge.is_connected()),
                "logged_in": bool(bridge.logged_in),
                "devices": len(devs) if isinstance(devs, dict) else len(list(devs)),
                "scenes": len(scenes_map)
                if isinstance(scenes_map, dict)
                else len(list(scenes_map)),
                "areas": len(areas_map) if isinstance(areas_map, dict) else len(list(areas_map)),
                "versions": {
                    "lutron_cli": pkg_version("lutron-cli"),
                    "pylutron_caseta": pkg_version("pylutron-caseta"),
                },
            }

    _json(run_async(_info()))


# ---------------------------------------------------------------------------
# Phase 4: export — full snapshot of bridge state for backup / diffing
# ---------------------------------------------------------------------------
@cli.command()
@click.pass_context
def export(ctx):
    """Dump a full JSON snapshot of areas, devices, scenes, and occupancy groups."""
    host = _resolve_host(ctx.obj["host"])

    async def _export():
        async with open_bridge(host) as bridge:
            def _listify(d):
                return list(d.values()) if isinstance(d, dict) else (d or [])

            return {
                "host": host,
                "areas": _listify(bridge.areas),
                "devices": _listify(bridge.get_devices()),
                "scenes": _listify(bridge.get_scenes()),
                "occupancy_groups": _listify(bridge.occupancy_groups),
                "buttons": _listify(bridge.get_buttons()),
            }

    _json(run_async(_export()))
