"""Lutron Caseta CLI - Click command group and all subcommands."""

from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from pathlib import Path

import click

from .bridge import get_cert_dir, get_cert_paths, open_bridge, run_async
from .config import get_default_host, load_config, save_config, set_default_host


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
    from zeroconf import ServiceBrowser, ServiceStateChange, Zeroconf
    import socket
    import threading

    results = []
    done = threading.Event()

    def on_state_change(zc, service_type, name, state_change):
        if state_change is ServiceStateChange.Added:
            info = zc.get_service_info(service_type, name)
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
    """Pair with a Lutron Caseta bridge. Press the small black button on the back of the bridge when prompted."""

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
