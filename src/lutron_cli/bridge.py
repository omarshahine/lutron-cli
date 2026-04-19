"""Bridge connection and certificate resolution for Lutron Caseta."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import click
from pylutron_caseta.smartbridge import Smartbridge
from xdg import xdg_config_home


def get_cert_dir() -> Path:
    """Return the pylutron_caseta certificate directory."""
    return xdg_config_home() / "pylutron_caseta"


def get_cert_paths(host: str) -> tuple[Path, Path, Path]:
    """Return (key_path, cert_path, ca_path) for a given bridge host."""
    cert_dir = get_cert_dir()
    return (
        cert_dir / f"{host}.key",
        cert_dir / f"{host}.crt",
        cert_dir / f"{host}-bridge.crt",
    )


def check_certs_exist(host: str) -> None:
    """Raise ClickException if cert files are missing."""
    key_path, cert_path, ca_path = get_cert_paths(host)
    missing = [p for p in (key_path, cert_path, ca_path) if not p.exists()]
    if missing:
        names = ", ".join(p.name for p in missing)
        raise click.ClickException(
            f"Missing certificate files: {names}\n"
            f"Run 'lutron pair {host}' to pair with the bridge first."
        )


async def connect_bridge(host: str) -> Smartbridge:
    """Create and connect a Smartbridge instance. Caller must close it."""
    check_certs_exist(host)
    key_path, cert_path, ca_path = get_cert_paths(host)
    bridge = Smartbridge.create_tls(
        hostname=host,
        keyfile=str(key_path),
        certfile=str(cert_path),
        ca_certs=str(ca_path),
    )
    await bridge.connect()
    return bridge


@asynccontextmanager
async def open_bridge(host: str) -> AsyncIterator[Smartbridge]:
    """Context manager that connects and always closes the bridge."""
    bridge = await connect_bridge(host)
    try:
        yield bridge
    finally:
        await bridge.close()


def run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)
