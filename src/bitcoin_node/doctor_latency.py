"""TCP + lightweight version-handshake latency probes for doctor."""

from __future__ import annotations

import asyncio
import time
from typing import Callable

from bitcoin_node.p2p.constants import MAINNET_MAGIC, TESTNET_MAGIC
from bitcoin_node.p2p.framing import encode_message
from bitcoin_node.p2p.serialize import build_version_payload


async def probe_peer_latency(
    host: str,
    port: int,
    *,
    network: str,
    timeout: float = 10.0,
    wire_log: Callable[[str, bytes], None] | None = None,
) -> tuple[float | None, float | None, str]:
    """Return (tcp_connect_ms, first_version_roundtrip_ms_or_none, status).

    Measures TCP connect time, sends `version`, reads first message (usually peer `version`),
    replies with `verack`, then exits.
    """
    magic = TESTNET_MAGIC if network == "testnet" else MAINNET_MAGIC
    t0 = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    except Exception as e:
        return None, None, f"connect failed: {e}"
    tcp_ms = (time.perf_counter() - t0) * 1000.0

    payload = build_version_payload()
    frame = encode_message(magic, "version", payload)
    if wire_log:
        wire_log(b"send version", frame)
    t1 = time.perf_counter()
    writer.write(frame)
    await writer.drain()

    # Read one full message
    try:
        hdr = await asyncio.wait_for(_read_exact(reader, 24), timeout=timeout)
        if wire_log:
            wire_log(b"recv header", hdr)
        if hdr[:4] != magic:
            writer.close()
            return tcp_ms, None, "wrong network magic"
        cmd = hdr[4:16].split(b"\x00", 1)[0].decode("ascii")
        ln = int.from_bytes(hdr[16:20], "little")
        payload_in = await asyncio.wait_for(_read_exact(reader, ln), timeout=timeout)
        if wire_log:
            wire_log(b"recv payload", payload_in)
        rtt_ms = (time.perf_counter() - t1) * 1000.0
        # send verack to be polite
        ack = encode_message(magic, "verack", b"")
        if wire_log:
            wire_log(b"send verack", ack)
        writer.write(ack)
        await writer.drain()
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return tcp_ms, rtt_ms, f"first msg: {cmd} ({len(payload_in)} payload bytes)"
    except Exception as e:
        writer.close()
        return tcp_ms, None, f"handshake read failed: {e}"


async def _read_exact(reader: asyncio.StreamReader, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = await reader.read(n - len(buf))
        if not chunk:
            raise ConnectionError("eof")
        buf.extend(chunk)
    return bytes(buf)
