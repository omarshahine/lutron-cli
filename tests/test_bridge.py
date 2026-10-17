"""Regression tests for the bridge TLS connection (no physical bridge needed)."""

from __future__ import annotations

import asyncio
import socket
import ssl

from lutron_cli import bridge


def _stub_loads(monkeypatch):
    calls = {}
    monkeypatch.setattr(
        ssl.SSLContext,
        "load_verify_locations",
        lambda self, cafile: calls.setdefault("ca", cafile),
    )
    monkeypatch.setattr(
        ssl.SSLContext,
        "load_cert_chain",
        lambda self, certfile, keyfile: calls.update(cert=certfile, key=keyfile),
    )
    return calls


def test_tls_context_disables_hostname_check_but_requires_cert(monkeypatch, tmp_path):
    calls = _stub_loads(monkeypatch)
    key, cert, ca = tmp_path / "h.key", tmp_path / "h.crt", tmp_path / "h-bridge.crt"

    ctx = bridge._create_tls_context(key, cert, ca)

    assert ctx.check_hostname is False
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.minimum_version == ssl.TLSVersion.TLSv1_2
    assert calls == {"ca": str(ca), "cert": str(cert), "key": str(key)}


def test_connect_bridge_passes_context_to_open_connection(monkeypatch, tmp_path):
    _stub_loads(monkeypatch)
    monkeypatch.setattr(bridge, "get_cert_dir", lambda: tmp_path)
    for p in bridge.get_cert_paths("10.0.0.5"):
        p.touch()

    seen = {}

    async def fake_open_connection(host, port, **kwargs):
        seen.update(host=host, port=port, **kwargs)
        return object()

    async def fake_connect(self):
        await self._connect()

    monkeypatch.setattr(bridge, "open_connection", fake_open_connection)
    monkeypatch.setattr(bridge.Smartbridge, "connect", fake_connect)

    asyncio.run(bridge.connect_bridge("10.0.0.5"))

    assert seen["host"] == "10.0.0.5"
    assert seen["port"] == bridge.LEAP_PORT
    assert seen["server_hostname"] == ""
    assert seen["family"] == socket.AF_INET
    assert isinstance(seen["ssl"], ssl.SSLContext)
    assert seen["ssl"].check_hostname is False
