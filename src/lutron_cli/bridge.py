"""Bridge connection and certificate resolution for Lutron Caseta."""

from __future__ import annotations

import asyncio
import socket
import ssl
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import click
from pylutron_caseta.leap import open_connection
from pylutron_caseta.smartbridge import LEAP_PORT, Smartbridge
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


def _create_tls_context(key_path: Path, cert_path: Path, ca_path: Path) -> ssl.SSLContext:
    """TLS context pinned to the bridge's own CA.

    The bridge cert is not issued for its IP, so hostname checking must be
    off. pylutron_caseta's create_tls leaves it on while passing
    server_hostname="", which Python 3.13 rejects with "check_hostname
    requires server_hostname" and Smartbridge then retries forever.
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.check_hostname = False
    ctx.load_verify_locations(str(ca_path))
    ctx.load_cert_chain(str(cert_path), str(key_path))
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx


async def connect_bridge(host: str) -> Smartbridge:
    """Create and connect a Smartbridge instance. Caller must close it."""
    check_certs_exist(host)
    key_path, cert_path, ca_path = get_cert_paths(host)

    async def _connect():
        ctx = await asyncio.get_running_loop().run_in_executor(
            None, _create_tls_context, key_path, cert_path, ca_path
        )
        return await open_connection(
            host, LEAP_PORT, server_hostname="", ssl=ctx, family=socket.AF_INET
        )

    bridge = Smartbridge(_connect)
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
