"""Async Bitcoin P2P client — handshake + transaction relay."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from bitcoin_node.p2p.constants import TESTNET_MAGIC
from bitcoin_node.p2p.framing import decode_message_header, encode_message, verify_payload_checksum
from bitcoin_node.p2p.serialize import build_inv_tx_vector, build_version_payload

LOG = logging.getLogger(__name__)

WireDebugFn = Callable[[str, bytes], None]


async def _read_exact(reader: asyncio.StreamReader, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = await reader.read(n - len(buf))
        if not chunk:
            raise ConnectionError("peer closed stream")
        buf.extend(chunk)
    return bytes(buf)


class BitcoinPeer:
    """Minimal outbound peer session."""

    def __init__(
        self,
        magic: bytes = TESTNET_MAGIC,
        *,
        relay: bool = False,
        wire_debug: WireDebugFn | None = None,
    ) -> None:
        self._magic = magic
        self._relay = relay
        self._wire_debug = wire_debug
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    def _dbg_send(self, label: str, frame: bytes) -> None:
        if self._wire_debug:
            self._wire_debug(f"send {label}", frame)

    def _dbg_recv(self, label: str, frame: bytes) -> None:
        if self._wire_debug:
            self._wire_debug(f"recv {label}", frame)

    async def connect(self, host: str, port: int, *, timeout: float = 15.0) -> None:
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        LOG.info("connected to %s:%s", host, port)

    async def close(self) -> None:
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader = None
        self._writer = None

    async def handshake(self, *, start_height: int = 0, timeout: float = 20.0) -> None:
        assert self._reader and self._writer

        async def _run() -> None:
            payload_v = build_version_payload(start_height=start_height, relay=self._relay)
            vframe = encode_message(self._magic, "version", payload_v)
            self._dbg_send("version", vframe)
            self._writer.write(vframe)
            await self._writer.drain()

            saw_peer_version = False
            saw_peer_verack = False
            while not saw_peer_verack:
                cmd, pl = await self._read_next_payload()
                if cmd == "version":
                    saw_peer_version = True
                    aframe = encode_message(self._magic, "verack", b"")
                    self._dbg_send("verack", aframe)
                    self._writer.write(aframe)
                    await self._writer.drain()
                elif cmd == "verack":
                    if saw_peer_version:
                        saw_peer_verack = True
                elif cmd == "ping":
                    self._writer.write(encode_message(self._magic, "pong", pl))
                    await self._writer.drain()
                elif cmd == "sendheaders":
                    continue
                else:
                    LOG.debug("handshake ignoring %s", cmd)

            if not saw_peer_version:
                raise RuntimeError("peer never advertised version")

        await asyncio.wait_for(_run(), timeout=timeout)

    async def send_inv_tx(self, txid_le: bytes) -> None:
        """Announce tx hash (32-byte LE wire-order)."""
        assert self._writer
        body = build_inv_tx_vector([txid_le])
        iframe = encode_message(self._magic, "inv", body)
        self._dbg_send("inv", iframe)
        self._writer.write(iframe)
        await self._writer.drain()

    async def send_tx(self, raw_tx: bytes) -> None:
        """Best-effort direct tx relay (modern nodes may ignore unsolicited tx)."""
        assert self._writer
        tframe = encode_message(self._magic, "tx", raw_tx)
        self._dbg_send("tx", tframe)
        self._writer.write(tframe)
        await self._writer.drain()

    async def drain_ping_pong(self, idle_rounds: int = 3) -> None:
        """Read and respond to ping for a few cycles — keeps socket alive briefly."""
        assert self._reader and self._writer
        for _ in range(idle_rounds):
            try:
                cmd, payload = await asyncio.wait_for(self._read_next_payload(), timeout=2.0)
            except TimeoutError:
                return
            if cmd == "ping":
                pframe = encode_message(self._magic, "pong", payload)
                self._dbg_send("pong", pframe)
                self._writer.write(pframe)
                await self._writer.drain()

    async def _read_next_payload(self) -> tuple[str, bytes]:
        assert self._reader
        hdr = await _read_exact(self._reader, 24)
        if hdr[:4] != self._magic:
            raise ValueError("wrong network magic")
        cmd, ln, chk = decode_message_header(hdr)
        payload = await _read_exact(self._reader, ln)
        self._dbg_recv(cmd, hdr + payload)
        verify_payload_checksum(payload, chk)
        return cmd, payload
